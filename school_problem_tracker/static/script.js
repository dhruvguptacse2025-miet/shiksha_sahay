console.log("SchoolCare loaded successfully");


// Confirm before submitting important actions

document.addEventListener("DOMContentLoaded", function () {

    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {

        form.addEventListener("submit", function () {

            console.log("Form submitted");

        });

    });

});