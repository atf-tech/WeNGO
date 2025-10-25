// custom.js
$(document).ready(function() {
    console.log("jQuery version:", $.fn.jquery);
    console.log("Has datepicker?", !!$.fn.datepicker);

    $("#dob").datepicker({
        changeMonth: true,
        changeYear: true,
        yearRange: "1900:2025",
        dateFormat: "dd/mm/yy",
        maxDate: 0,
        showAnim: "slideDown"
    });
});
