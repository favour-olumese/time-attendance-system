document.addEventListener('DOMContentLoaded', function () {
    const roleField = document.querySelector('#id_User_Role');
    const matricField = document.querySelector('#id_MatricNumber').closest('.form-row');
    const levelField = document.querySelector('#id_Level').closest('.form-row');

    function toggleFields() {
        if (roleField.value === 'Student') {
            matricField.style.display = '';
            levelField.style.display = '';
        } else {
            matricField.style.display = 'none';
            levelField.style.display = 'none';
        }
    }

    // Initial toggle on page load
    toggleFields();

    // Listen for changes in role
    roleField.addEventListener('change', toggleFields);
});
