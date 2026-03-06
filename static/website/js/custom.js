// custom.js
$(document).ready(function () {
    console.log("jQuery version:", $.fn.jquery);
    console.log("Has datepicker?", !!$.fn.datepicker);

    // ── Datepicker ────────────────────────────────────────────────
    $("#dob").datepicker({
        changeMonth: true,
        changeYear: true,
        yearRange: "1900:2025",
        dateFormat: "dd/mm/yy",
        maxDate: 0,
        showAnim: "slideDown"
    });

    // ── Donation Quantity & Amount Calculator ─────────────────────
    var unitPrice = parseInt($("#unit-price").text(), 10);  // reads from HTML
    var unitLabel = $("#unit-price").data("unit");          // reads from HTML

    function updateAmount(qty) {
        qty = parseInt(qty, 10);
        if (isNaN(qty) || qty < 1) qty = 1;

        $("#quantity-input").val(qty);

        $(".qty-btn").removeClass("active").filter(function () {
            return parseInt($(this).data("qty"), 10) === qty;
        }).addClass("active");

        var total = qty * unitPrice;
        $("#donation-amount").val(total);
        $("#amount-breakdown").text(
            qty + " " + unitLabel + "s × ₹" + unitPrice + " = ₹" + total.toLocaleString("en-IN")
        );
    }

    // ── Read default qty from HTML input — not hardcoded ──────────
    var defaultQty = parseInt($("#quantity-input").val(), 10) || 1;
    updateAmount(defaultQty);

    $(document).on("click", ".qty-btn", function () {
        updateAmount($(this).data("qty"));
    });

    $(document).on("input", "#quantity-input", function () {
        updateAmount($(this).val());
    });

    $(document).on("click", "#qty-plus", function () {
        var current = parseInt($("#quantity-input").val(), 10) || 0;
        updateAmount(current + 1);
    });

    $(document).on("click", "#qty-minus", function () {
        var current = parseInt($("#quantity-input").val(), 10) || 1;
        if (current > 1) updateAmount(current - 1);
    });

    // ── End Donation Calculator ───────────────────────────────────
});