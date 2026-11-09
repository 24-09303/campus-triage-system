import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = 'batstateu_cpe411_medtriage_secret_key_2025'

# ==============================================================================
# DATA STRUCTURE IMPLEMENTATIONS (DSA REQUIREMENTS)
# ==============================================================================

class MaxHeap:
    """Max-Heap for Emergency Triage Queue (Priority Queue)."""
    def __init__(self):
        self.heap = []

    def insert(self, patient):
        self.heap.append(patient)
        self._heapify_up(len(self.heap) - 1)

    def extract_max(self):
        if not self.heap:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        
        root = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._heapify_down(0)
        return root

    def peek(self):
        return self.heap[0] if self.heap else None

    def _heapify_up(self, index):
        parent = (index - 1) // 2
        if index > 0 and self.heap[index]['severity'] > self.heap[parent]['severity']:
            self.heap[index], self.heap[parent] = self.heap[parent], self.heap[index]
            self._heapify_up(parent)

    def _heapify_down(self, index):
        largest = index
        left = 2 * index + 1
        right = 2 * index + 2
        size = len(self.heap)

        if left < size and self.heap[left]['severity'] > self.heap[largest]['severity']:
            largest = left
        if right < size and self.heap[right]['severity'] > self.heap[largest]['severity']:
            largest = right

        if largest != index:
            self.heap[index], self.heap[largest] = self.heap[largest], self.heap[index]
            self._heapify_down(largest)

    def get_all(self):
        return sorted(self.heap, key=lambda x: x['severity'], reverse=True)

    def size(self):
        return len(self.heap)


class PatientQueue:
    """FIFO Queue for Routine Non-Emergency Patients."""
    def __init__(self):
        self.queue = []

    def enqueue(self, patient):
        self.queue.append(patient)

    def dequeue(self):
        if not self.queue:
            return None
        return self.queue.pop(0)

    def peek(self):
        return self.queue[0] if self.queue else None

    def get_all(self):
        return list(self.queue)

    def size(self):
        return len(self.queue)


class BSTNode:
    """Binary Search Tree Node for Patient Records."""
    def __init__(self, patient):
        self.patient = patient
        self.left = None
        self.right = None


class PatientBST:
    """Binary Search Tree for O(log n) Patient ID Lookup."""
    def __init__(self):
        self.root = None

    def insert(self, patient):
        new_node = BSTNode(patient)
        if not self.root:
            self.root = new_node
            return True
        
        curr = self.root
        while True:
            if patient['id'] == curr.patient['id']:
                return False  # Duplicate ID
            elif patient['id'] < curr.patient['id']:
                if curr.left is None:
                    curr.left = new_node
                    return True
                curr = curr.left
            else:
                if curr.right is None:
                    curr.right = new_node
                    return True
                curr = curr.right

    def search(self, patient_id):
        curr = self.root
        comparisons = 0
        while curr:
            comparisons += 1
            if patient_id == curr.patient['id']:
                return curr.patient, comparisons
            elif patient_id < curr.patient['id']:
                curr = curr.left
            else:
                curr = curr.right
        return None, comparisons

    def to_dict(self, node=None):
        if node is None:
            node = self.root
        if not node:
            return None
        return {
            'id': node.patient['id'],
            'name': node.patient['name'],
            'severity': node.patient['severity'],
            'left': self.to_dict(node.left) if node.left else None,
            'right': self.to_dict(node.right) if node.right else None
        }


# ==============================================================================
# GLOBAL STATE INITIALIZATION
# ==============================================================================

triage_heap = MaxHeap()
routine_queue = PatientQueue()
patient_bst = PatientBST()
treatment_history = []

stats = {
    'total_registered': 0,
    'total_treated': 0,
    'emergencies_handled': 0,
    'routine_handled': 0
}

# Add default seed data for demonstration
seed_patients = [
    {"name": "Juan Dela Cruz", "id": "21-01234", "type": "Emergency", "severity": 9, "symptoms": "Chest pain, shortness of breath", "age": 21, "gender": "Male", "contact": "09171234567"},
    {"name": "Maria Santos", "id": "22-05678", "type": "Routine", "severity": 3, "symptoms": "Mild headache and fatigue", "age": 19, "gender": "Female", "contact": "09189876543"},
    {"name": "Carlos Reyes", "id": "20-09988", "type": "Emergency", "severity": 7, "symptoms": "High fever with chills", "age": 22, "gender": "Male", "contact": "09205554433"},
    {"name": "Ana Lim", "id": "23-04321", "type": "Routine", "severity": 2, "symptoms": "Medical certificate request", "age": 20, "gender": "Female", "contact": "09191112233"}
]

for p in seed_patients:
    p['registered_at'] = datetime.now().strftime('%I:%M:%S %p')
    if patient_bst.insert(p):
        stats['total_registered'] += 1
        if p['type'] == 'Emergency':
            triage_heap.insert(p)
        else:
            routine_queue.enqueue(p)

# ==============================================================================
# ROUTES & CONTROLLERS
# ==============================================================================

@app.route('/')
def home():
    return render_template('index.html')

# --- AUTHENTICATION ENDPOINTS ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if username == 'admin' and password == 'batstateu411':
        session['role'] = 'admin'
        return jsonify({'success': True, 'role': 'admin', 'message': 'Welcome, Administrator!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid admin credentials!'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('role', None)
    return jsonify({'success': True, 'message': 'Logged out successfully.'})


@app.route('/api/auth_status', methods=['GET'])
def auth_status():
    return jsonify({
        'role': session.get('role', 'patient'),
        'is_admin': session.get('role') == 'admin'
    })


# --- PUBLIC / PATIENT ENDPOINTS ---

@app.route('/api/add_patient', methods=['POST'])
def add_patient():
    data = request.json or {}
    
    if not data.get('name') or not data.get('id'):
        return jsonify({'success': False, 'error': 'Name and Student ID are required!'}), 400

    patient = {
        'name': data.get('name'),
        'id': data.get('id'),
        'type': data.get('type', 'Routine'),
        'severity': int(data.get('severity', 1)),
        'symptoms': data.get('symptoms', 'None specified'),
        'age': data.get('age', 'N/A'),
        'gender': data.get('gender', 'N/A'),
        'contact': data.get('contact', 'N/A'),
        'registered_at': datetime.now().strftime('%I:%M:%S %p')
    }

    if not patient_bst.insert(patient):
        return jsonify({'success': False, 'error': f"Student ID '{patient['id']}' is already registered!"}), 400

    stats['total_registered'] += 1

    if patient['type'] == 'Emergency':
        triage_heap.insert(patient)
    else:
        routine_queue.enqueue(patient)

    return jsonify({'success': True, 'message': f"Patient {patient['name']} registered successfully!", 'patient': patient})


@app.route('/api/my_status', methods=['POST'])
def my_status():
    """Allows a patient to securely look up their own current queue status."""
    data = request.json or {}
    patient_id = data.get('id', '').strip()

    if not patient_id:
        return jsonify({'success': False, 'error': 'Please enter a Student ID.'}), 400

    patient, _ = patient_bst.search(patient_id)
    if not patient:
        return jsonify({'success': False, 'found': False, 'message': 'No record found for this Student ID.'})

    # Check if already treated
    treated_record = next((t for t in treatment_history if t['id'] == patient_id), None)
    if treated_record:
        return jsonify({
            'success': True,
            'found': True,
            'status': 'Treated',
            'patient': patient,
            'treated_at': treated_record.get('treated_at')
        })

    # Find position in Emergency Heap
    if patient['type'] == 'Emergency':
        heap_list = triage_heap.get_all()
        pos = next((i + 1 for i, p in enumerate(heap_list) if p['id'] == patient_id), None)
        return jsonify({
            'success': True,
            'found': True,
            'status': 'Waiting (Emergency Triage)',
            'position': pos,
            'queue_size': len(heap_list),
            'patient': patient
        })

    # Find position in Routine Queue
    routine_list = routine_queue.get_all()
    pos = next((i + 1 for i, p in enumerate(routine_list) if p['id'] == patient_id), None)
    return jsonify({
        'success': True,
        'found': True,
        'status': 'Waiting (Routine Queue)',
        'position': pos,
        'queue_size': len(routine_list),
        'patient': patient
    })


@app.route('/api/get_stats', methods=['GET'])
def get_stats():
    return jsonify({
        'stats': stats,
        'emergency_queue': triage_heap.get_all(),
        'routine_queue': routine_queue.get_all(),
        'history': treatment_history,
        'is_admin': session.get('role') == 'admin'
    })


# --- ADMIN ONLY ENDPOINTS ---

def require_admin():
    return session.get('role') == 'admin'


@app.route('/api/next_emergency', methods=['POST'])
def next_emergency():
    if not require_admin():
        return jsonify({'success': False, 'error': 'Admin authorization required!'}), 403

    patient = triage_heap.extract_max()
    if not patient:
        return jsonify({'success': False, 'error': 'No emergency patients in queue!'}), 404

    patient['treated_at'] = datetime.now().strftime('%I:%M:%S %p')
    treatment_history.insert(0, patient)
    stats['total_treated'] += 1
    stats['emergencies_handled'] += 1

    return jsonify({'success': True, 'patient': patient})


@app.route('/api/next_routine', methods=['POST'])
def next_routine():
    if not require_admin():
        return jsonify({'success': False, 'error': 'Admin authorization required!'}), 403

    patient = routine_queue.dequeue()
    if not patient:
        return jsonify({'success': False, 'error': 'No routine patients in queue!'}), 404

    patient['treated_at'] = datetime.now().strftime('%I:%M:%S %p')
    treatment_history.insert(0, patient)
    stats['total_treated'] += 1
    stats['routine_handled'] += 1

    return jsonify({'success': True, 'patient': patient})


@app.route('/api/search_patient', methods=['POST'])
def search_patient():
    if not require_admin():
        return jsonify({'success': False, 'error': 'Admin authorization required!'}), 403

    patient_id = (request.json or {}).get('id', '').strip()
    
    # BST Search
    t0 = time.perf_counter()
    patient_bst_res, bst_comps = patient_bst.search(patient_id)
    t1 = time.perf_counter()
    bst_time = (t1 - t0) * 1000  # ms

    # Linear Search on history + current
    all_patients = triage_heap.get_all() + routine_queue.get_all() + treatment_history
    t2 = time.perf_counter()
    linear_res = None
    linear_comps = 0
    for p in all_patients:
        linear_comps += 1
        if p['id'] == patient_id:
            linear_res = p
            break
    t3 = time.perf_counter()
    linear_time = (t3 - t2) * 1000  # ms

    return jsonify({
        'found': patient_bst_res is not None,
        'patient': patient_bst_res,
        'metrics': {
            'bst_time_ms': round(bst_time, 5),
            'bst_comparisons': bst_comps,
            'linear_time_ms': round(linear_time, 5),
            'linear_comparisons': linear_comps
        }
    })


@app.route('/api/benchmark', methods=['POST'])
def benchmark():
    if not require_admin():
        return jsonify({'success': False, 'error': 'Admin authorization required!'}), 403

    sizes = [100, 1000, 10000]
    results = []

    for size in sizes:
        dataset = list(range(0, size * 2, 2))
        target = dataset[-1]

        # Linear Search Worst Case
        t0 = time.perf_counter()
        linear_found = False
        lin_comps = 0
        for x in dataset:
            lin_comps += 1
            if x == target:
                linear_found = True
                break
        t1 = time.perf_counter()
        linear_time = (t1 - t0) * 1000

        # Binary Search Worst Case
        t2 = time.perf_counter()
        low, high = 0, len(dataset) - 1
        bin_comps = 0
        bin_found = False
        while low <= high:
            bin_comps += 1
            mid = (low + high) // 2
            if dataset[mid] == target:
                bin_found = True
                break
            elif dataset[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
        t3 = time.perf_counter()
        binary_time = (t3 - t2) * 1000

        speedup = round(linear_time / binary_time, 2) if binary_time > 0 else "N/A"

        results.append({
            'size': size,
            'linear_ms': round(linear_time, 4),
            'linear_comps': lin_comps,
            'binary_ms': round(binary_time, 4),
            'binary_comps': bin_comps,
            'speedup': speedup
        })

    return jsonify({'results': results})


@app.route('/api/get_tree', methods=['GET'])
def get_tree():
    if not require_admin():
        return jsonify({'success': False, 'error': 'Admin authorization required!'}), 403

    return jsonify({'tree': patient_bst.to_dict()})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
