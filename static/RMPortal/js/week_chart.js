
const weekValues = window.weekValues || [];
const weekCategories = window.weekCategories || [];


var options = {

    series: weekValues,

    chart: {
        width: 520,
        type: 'donut',
        toolbar: {
            show: false
        }
    },

    labels: weekCategories,

    colors: [
        '#6C63FF',
        '#FF6B81',
        '#FFC75F',
        '#00C9A7',
        '#4D96FF',
        '#B983FF',
        '#FF9671'
    ],

    plotOptions: {
        pie: {
            expandOnClick: true,
            donut: {
                size: '68%',
                labels: {
                    show: true,

                    total: {
                        show: true,
                        label: 'Total',

                        formatter: function (w) {
                            const total = w.globals.seriesTotals.reduce(
                                (a, b) => a + b,
                                0
                            );

                            return '₹' + total.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    },

    dataLabels: {

        enabled: true,

        formatter: function (val, opts) {

            const amount = opts.w.config.series[opts.seriesIndex];

            return '₹' + Number(amount).toLocaleString('en-IN');
        }
    },

    stroke: {
        width: 4,
        colors: ['#fff']
    },

    legend: {

        show: true,

        position: 'right',

        fontSize: '14px',

        formatter: function (seriesName, opts) {

            const amount = opts.w.globals.series[opts.seriesIndex];

            return seriesName + ' - ₹' + Number(amount).toLocaleString('en-IN');
        }
    },

    tooltip: {

        y: {

            formatter: function (val) {

                return '₹' + Number(val).toLocaleString('en-IN');
            }
        }
    }
};

var chart = new ApexCharts(
    document.querySelector("#month_pike"),
    options
);

chart.render();

