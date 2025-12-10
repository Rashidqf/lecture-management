// Admin Teachers Management
let teachers = [];
let editingId = null;

// Load teachers from API
async function loadTeachers() {
    try {
        const response = await api.getTeachers();
        teachers = Array.isArray(response) ? response : [];
        displayTeachers(teachers);
    } catch (error) {
        console.error('Error loading teachers:', error);
        showError('Failed to load teachers. Please refresh the page.');
    }
}

// Display teachers in table
function displayTeachers(teacherList) {
    const tbody = document.getElementById('teachersTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (teacherList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">No teachers found</td></tr>';
        return;
    }

    teacherList.forEach(teacher => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${teacher.id}</td>
            <td>${teacher.username}</td>
            <td>${teacher.email}</td>
            <td>${teacher.phone || 'N/A'}</td>
            <td>N/A</td>
            <td>N/A</td>
            <td>${new Date(teacher.created_at).toLocaleDateString()}</td>
            <td><span class="badge ${teacher.status === 'Active' ? 'bg-success' : 'bg-secondary'}">${teacher.status}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editTeacher(${teacher.id})">
                    <i class="ti-pencil"></i> Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteTeacher(${teacher.id})">
                    <i class="ti-trash"></i> Delete
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Edit teacher
async function editTeacher(id) {
    const teacher = teachers.find(t => t.id === id);
    if (teacher) {
        editingId = id;
        document.getElementById('teacherId').value = teacher.id;
        document.getElementById('teacherName').value = teacher.username;
        document.getElementById('teacherEmail').value = teacher.email;
        document.getElementById('teacherPhone').value = teacher.phone || '';
        document.getElementById('teacherStatus').value = teacher.status;
        document.getElementById('addTeacherModalLabel').textContent = 'Edit Teacher';
        $('#addTeacherModal').modal('show');
    }
}

// Delete teacher
async function deleteTeacher(id) {
    if (!confirm('Are you sure you want to delete this teacher?')) {
        return;
    }

    try {
        const result = await api.deleteTeacher(id);
        if (result.success) {
            await loadTeachers();
            showSuccess('Teacher deleted successfully!');
        } else {
            showError(result.message || 'Failed to delete teacher');
        }
    } catch (error) {
        console.error('Error deleting teacher:', error);
        showError('Failed to delete teacher. Please try again.');
    }
}

// Save teacher (add or update)
async function saveTeacher() {
    const form = document.getElementById('teacherForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const teacherData = {
        username: document.getElementById('teacherName').value,
        email: document.getElementById('teacherEmail').value,
        phone: document.getElementById('teacherPhone').value,
        status: document.getElementById('teacherStatus').value
    };

    try {
        let result;
        if (editingId) {
            result = await api.updateTeacher(editingId, teacherData);
        } else {
            result = await api.registerTeacher({
                ...teacherData,
                password: 'default123' // Default password, admin can change later
            });
        }

        if (result.success) {
            await loadTeachers();
            $('#addTeacherModal').modal('hide');
            form.reset();
            editingId = null;
            document.getElementById('addTeacherModalLabel').textContent = 'Add New Teacher';
            showSuccess(editingId ? 'Teacher updated successfully!' : 'Teacher registered successfully!');
        } else {
            showError(result.message || 'Failed to save teacher');
        }
    } catch (error) {
        console.error('Error saving teacher:', error);
        showError('Failed to save teacher. Please try again.');
    }
}

// Search and filter
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchTeacher');
    const filterDepartment = document.getElementById('filterDepartment');

    if (searchInput) {
        searchInput.addEventListener('input', filterTeachers);
    }
    if (filterDepartment) {
        filterDepartment.addEventListener('change', filterTeachers);
    }
});

function filterTeachers() {
    const searchTerm = document.getElementById('searchTeacher')?.value.toLowerCase() || '';
    const departmentFilter = document.getElementById('filterDepartment')?.value || '';

    let filtered = teachers.filter(teacher => {
        const matchesSearch = teacher.username?.toLowerCase().includes(searchTerm) ||
            teacher.email?.toLowerCase().includes(searchTerm);
        // For now, department filter is not implemented in backend
        return matchesSearch;
    });

    displayTeachers(filtered);
}

function clearFilters() {
    document.getElementById('searchTeacher').value = '';
    document.getElementById('filterDepartment').value = '';
    displayTeachers(teachers);
}

// Reset form when modal is closed
$(document).ready(function() {
    $('#addTeacherModal').on('hidden.bs.modal', function() {
        document.getElementById('teacherForm').reset();
        editingId = null;
        document.getElementById('addTeacherModalLabel').textContent = 'Add New Teacher';
    });
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', async function() {
    if (await adminManager.checkAuth()) {
        await loadTeachers();
    }
});

// Utility functions
function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert(message);
}


