// Admin Students Management
let students = [];
let editingId = null;

// Load students from API
async function loadStudents() {
    try {
        const response = await api.getStudents();
        students = Array.isArray(response) ? response : [];
        displayStudents(students);
    } catch (error) {
        console.error('Error loading students:', error);
        showError('Failed to load students. Please refresh the page.');
    }
}

// Display students in table
function displayStudents(studentList) {
    const tbody = document.getElementById('studentsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (studentList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No students found</td></tr>';
        return;
    }

    studentList.forEach(student => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${student.id}</td>
            <td>${student.username}</td>
            <td>${student.email}</td>
            <td>${student.phone || 'N/A'}</td>
            <td>${new Date(student.created_at).toLocaleDateString()}</td>
            <td><span class="badge ${student.status === 'Active' ? 'bg-success' : 'bg-secondary'}">${student.status}</span></td>
            <td>${student.role}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editStudent(${student.id})">
                    <i class="ti-pencil"></i> Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteStudent(${student.id})">
                    <i class="ti-trash"></i> Delete
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Edit student
async function editStudent(id) {
    const student = students.find(s => s.id === id);
    if (student) {
        editingId = id;
        document.getElementById('studentId').value = student.id;
        document.getElementById('studentName').value = student.username;
        document.getElementById('studentEmail').value = student.email;
        document.getElementById('studentPhone').value = student.phone || '';
        document.getElementById('studentStatus').value = student.status;
        document.getElementById('addStudentModalLabel').textContent = 'Edit Student';
        $('#addStudentModal').modal('show');
    }
}

// Delete student
async function deleteStudent(id) {
    if (!confirm('Are you sure you want to delete this student?')) {
        return;
    }

    try {
        const result = await api.deleteStudent(id);
        if (result.success) {
            await loadStudents();
            showSuccess('Student deleted successfully!');
        } else {
            showError(result.message || 'Failed to delete student');
        }
    } catch (error) {
        console.error('Error deleting student:', error);
        showError('Failed to delete student. Please try again.');
    }
}

// Save student (add or update)
async function saveStudent() {
    const form = document.getElementById('studentForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const studentData = {
        username: document.getElementById('studentName').value,
        email: document.getElementById('studentEmail').value,
        phone: document.getElementById('studentPhone').value,
        status: document.getElementById('studentStatus').value
    };

    try {
        let result;
        if (editingId) {
            result = await api.updateStudent(editingId, studentData);
        } else {
            result = await api.registerStudent({
                ...studentData,
                password: 'default123' // Default password, admin can change later
            });
        }

        if (result.success) {
            await loadStudents();
            $('#addStudentModal').modal('hide');
            form.reset();
            editingId = null;
            document.getElementById('addStudentModalLabel').textContent = 'Add New Student';
            showSuccess(editingId ? 'Student updated successfully!' : 'Student registered successfully!');
        } else {
            showError(result.message || 'Failed to save student');
        }
    } catch (error) {
        console.error('Error saving student:', error);
        showError('Failed to save student. Please try again.');
    }
}

// Search and filter
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchStudent');
    const filterStatus = document.getElementById('filterStatus');

    if (searchInput) {
        searchInput.addEventListener('input', filterStudents);
    }
    if (filterStatus) {
        filterStatus.addEventListener('change', filterStudents);
    }
});

function filterStudents() {
    const searchTerm = document.getElementById('searchStudent')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('filterStatus')?.value || '';

    let filtered = students.filter(student => {
        const matchesSearch = student.username?.toLowerCase().includes(searchTerm) ||
            student.email?.toLowerCase().includes(searchTerm);
        const matchesStatus = !statusFilter || student.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    displayStudents(filtered);
}

function clearFilters() {
    document.getElementById('searchStudent').value = '';
    document.getElementById('filterStatus').value = '';
    displayStudents(students);
}

// Reset form when modal is closed
$(document).ready(function() {
    $('#addStudentModal').on('hidden.bs.modal', function() {
        document.getElementById('studentForm').reset();
        editingId = null;
        document.getElementById('addStudentModalLabel').textContent = 'Add New Student';
    });
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', async function() {
    if (await adminManager.checkAuth()) {
        await loadStudents();
    }
});

// Utility functions
function showSuccess(message) {
    // You can use toastr, sweetalert, or simple alert
    alert(message);
}

function showError(message) {
    alert(message);
}


