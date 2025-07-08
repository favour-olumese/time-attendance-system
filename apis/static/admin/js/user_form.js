document.addEventListener('DOMContentLoaded', function () {
    /*
    This function hides the matric number and level field of the User model 
    until the student's role is chosen.
    */

    const roleField = document.querySelector('#id_user_role');
    const matricField = document.querySelector('#id_matric_number').closest('.form-row');
    const levelField = document.querySelector('#id_level').closest('.form-row');

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
