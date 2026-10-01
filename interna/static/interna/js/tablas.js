document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".js-datatable").forEach(function (elemento) {
        const opciones = {
            pageLength: 10,
            lengthMenu: [10, 25, 50],
            order: [[0, "asc"]],

            language: {
                search: "Buscar:",
                lengthMenu: "Mostrar _MENU_ Registros por Página",
                info: "Mostrando _START_ a _END_ de _TOTAL_ Registros",
                infoEmpty: "No hay Registros para Mostrar",
                infoFiltered: "(filtrados de _MAX_ registros en total)",
                emptyTable: "No hay Registros Disponibles",
                zeroRecords: "No se Encontraron Resultados",
                paginate: {
                    first: "Primera",
                    last: "Última",
                    next: "Siguiente",
                    previous: "Anterior"
                },
                aria: {
                    orderable: "Ordenar por esta Columna",
                    orderableReverse: "Invertir el Orden de esta Columna"
                }
            }
        };

        if (elemento.dataset.columnaAcciones !== undefined) {
            opciones.columnDefs = [{
                targets: Number(elemento.dataset.columnaAcciones),
                orderable: false,
                searchable: false
            }];
        }

        const tabla = new DataTable(elemento, opciones);
        const filtroId = elemento.dataset.filtroEstado;
        const columnaEstado = elemento.dataset.columnaEstado;

        if (filtroId && columnaEstado !== undefined) {
            const filtro = document.getElementById(filtroId);

            if (filtro) {
                filtro.addEventListener("change", function () {
                    tabla
                        .column(Number(columnaEstado))
                        .search(this.value, { exact: true })
                        .draw();
                });
            }
        }
    });
});