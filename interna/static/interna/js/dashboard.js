document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("grafico-ventas");
    const datos = document.getElementById("datos-ventas");

    if (!canvas || !datos) return;

    const ventas = JSON.parse(datos.textContent);

    const pesos = new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency: "CLP",
        maximumFractionDigits: 0
    });

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: ventas.map(function (venta) {
                return venta.fecha.split("-").reverse().join("/");
            }),
            datasets: [{
                label: "Ventas sin envío",
                data: ventas.map(function (venta) {
                    return Number(venta.total);
                }),
                backgroundColor: "#f38a6a",
                borderRadius: 6,
                maxBarThickness: 60
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function (contexto) {
                            return "Ventas: " + pesos.format(contexto.parsed.y);
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Fecha de creación del pedido"
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (valor) {
                            return pesos.format(valor);
                        }
                    }
                }
            }
        }
    });
});