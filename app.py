from flask import Flask, render_template, request, jsonify
import time
from datetime import datetime

app = Flask(__name__)

# ==========================================
# DATA STRUCTURES
# ==========================================

class MaxHeap:
    """Priority Queue using Max-Heap - Highest severity extracted first"""
    def __init__(self):
        self.heap = []
    
    def insert(self, patient):
        self.heap.append(patient)
        self._heapify_up(len(self.heap) - 1)
    
    def extract_max(self):
        if not self.heap: return None
        if len(self.heap) == 1: return self.heap.pop()
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
        left, right = 2 * index + 1, 2 * index + 2
        if left < len(self.heap) and self.heap[left]['severity'] > self.heap[largest]['severity']:
            largest = left
        if right < len(self.heap) and self.heap[right]['severity'] > self.heap[largest]['severity']:
            largest = right
        if largest != index:
            self.heap[index], self.heap[largest] = self.heap[largest], self.heap[index]
            self._heapify_down(largest)
    
    def get_all(self):
        return sorted(self.heap, key=lambda x: x['severity'], reverse=True)
    
    def size(self):
        return len(self.heap)


class PatientQueue:
    """FIFO Queue for routine patients"""
    def __init__(self):
        self.queue = []
    
    def enqueue(self, patient):
        self.queue.append(patient)
    
    def dequeue(self):
        return self.queue.pop(0) if self.queue else None
    
    def peek(self):
        return self.queue[0] if self.queue else None
    
    def get_all(self):
        return self.queue
    
    def size(self):
        return len(self.queue)


class BSTNode:
    def __init__(self, patient):
        self.patient = patient
        self.left = None
        self.right = None


class PatientBST:
    """Binary Search Tree for patient record lookup by ID"""
    def __init__(self):
        self.root = None
        self.count = 0
    
    def insert(self, patient):
        self.count += 1
        if not self.root:
            self.root = BSTNode(patient)
        else:
            self._insert_rec(self.root, patient)
    
    def _insert_rec(self, node, patient):
        if patient['id'] < node.patient['id']:
            if not node.left:
                node.left = BSTNode(patient)
            else:
                self._insert_rec(node.left, patient)
        else:
            if not node.right:
                node.right = BSTNode(patient)
            else:
                self._insert_rec(node.right, patient)
    
    def search(self, patient_id):
        return self._search_rec(self.root, patient_id)
    
    def _search_rec(self, node, patient_id):
        if not node: return None
        if node.patient['id'] == patient_id:
            return node.patient
        if patient_id < node.patient['id']:
            return self._search_rec(node.left, patient_id)
        return self._search_rec(node.right, patient_id)
    
    def to_dict(self):
        """Convert tree to dict for visualization"""
        return self._node_to_dict(self.root)
    
    def _node_to_dict(self, node):
        if not node: return None
        return {
            'patient': node.patient,
            'left': self._node_to_dict(node.left),
            'right': self._node_to_dict(node.right)
        }
    
    def inorder(self):
        result = []
        self._inorder_rec(self.root, result)
        return result
    
    def _inorder_rec(self, node, result):
        if node:
            self._inorder_rec(node.left, result)
            result.append(node.patient)
            self._inorder_rec(node.right, result)


# Global Instances
triage_heap = MaxHeap()
routine_queue = PatientQueue()
patient_bst = PatientBST()
treatment_history = []  # Log of all treated patients
stats = {
    'total_registered': 0,
    'total_treated': 0,
    'emergencies_handled': 0,
    'routine_handled': 0
}


# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    patient = {
        'name': data['name'],
        'id': int(data['id']),
        'type': data['type'],
        'severity': int(data.get('severity', 0)),
        'symptoms': data.get('symptoms', 'Not specified'),
        'age': int(data.get('age', 0)),
        'gender': data.get('gender', 'N/A'),
        'contact': data.get('contact', 'N/A'),
        'registered_at': datetime.now().strftime('%I:%M:%S %p')
    }
    
    # Check for duplicate ID
    if patient_bst.search(patient['id']):
        return jsonify({"error": f"Patient ID {patient['id']} already exists!"}), 400
    
    patient_bst.insert(patient)
    stats['total_registered'] += 1
    
    if patient['type'] == 'emergency':
        triage_heap.insert(patient)
    else:
        routine_queue.enqueue(patient)
    
    return jsonify({
        "success": True,
        "patient": patient,
        "triage": triage_heap.get_all(),
        "queue": routine_queue.get_all(),
        "stats": stats
    })


@app.route('/api/next_routine', methods=['POST'])
def next_routine():
    called = routine_queue.dequeue()
    if called:
        called['treated_at'] = datetime.now().strftime('%I:%M:%S %p')
        treatment_history.insert(0, called)
        stats['total_treated'] += 1
        stats['routine_handled'] += 1
    return jsonify({
        "called": called,
        "queue": routine_queue.get_all(),
        "history": treatment_history[:10],
        "stats": stats
    })


@app.route('/api/next_emergency', methods=['POST'])
def next_emergency():
    called = triage_heap.extract_max()
    if called:
        called['treated_at'] = datetime.now().strftime('%I:%M:%S %p')
        treatment_history.insert(0, called)
        stats['total_treated'] += 1
        stats['emergencies_handled'] += 1
    return jsonify({
        "called": called,
        "triage": triage_heap.get_all(),
        "history": treatment_history[:10],
        "stats": stats
    })


@app.route('/api/search_patient', methods=['POST'])
def search_patient():
    patient_id = int(request.json.get('id', 0))
    
    # Linear search comparison
    start = time.perf_counter()
    linear_result = None
    all_patients = patient_bst.inorder()
    for p in all_patients:
        if p['id'] == patient_id:
            linear_result = p
            break
    linear_time = (time.perf_counter() - start) * 1000
    
    # BST search
    start = time.perf_counter()
    bst_result = patient_bst.search(patient_id)
    bst_time = (time.perf_counter() - start) * 1000
    
    return jsonify({
        "patient": bst_result,
        "linear_time_ms": round(linear_time, 4),
        "bst_time_ms": round(bst_time, 4),
        "total_records": patient_bst.count
    })


@app.route('/api/benchmark', methods=['POST'])
def run_benchmark():
    size = int(request.json.get('size', 10000))
    dataset = [i * 2 for i in range(size)]
    target = dataset[size - 1]  # Worst case for linear
    
    # Linear Search O(N)
    start = time.perf_counter()
    for item in dataset:
        if item == target:
            break
    linear_time = (time.perf_counter() - start) * 1000
    
    # Binary Search O(log N)
    start = time.perf_counter()
    low, high = 0, len(dataset) - 1
    while low <= high:
        mid = (low + high) // 2
        if dataset[mid] == target:
            break
        elif dataset[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    binary_time = (time.perf_counter() - start) * 1000
    
    speedup = round(linear_time / binary_time, 2) if binary_time > 0 else 0
    
    return jsonify({
        "size": size,
        "linear_time_ms": round(linear_time, 4),
        "binary_time_ms": round(binary_time, 4),
        "speedup": speedup
    })


@app.route('/api/get_tree', methods=['GET'])
def get_tree():
    return jsonify({
        "tree": patient_bst.to_dict(),
        "count": patient_bst.count
    })


@app.route('/api/get_stats', methods=['GET'])
def get_stats():
    return jsonify({
        "stats": stats,
        "triage": triage_heap.get_all(),
        "queue": routine_queue.get_all(),
        "history": treatment_history[:10]
    })


if __name__ == '__main__':
    app.run(debug=True)
