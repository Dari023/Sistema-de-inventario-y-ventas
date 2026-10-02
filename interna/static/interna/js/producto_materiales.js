document.addEventListener("DOMContentLoaded", function () {
    const lista = document.getElementById("lista-materiales");

    if (!lista) return;

    const plantilla = document.getElementById("material-vacio");
    const total = document.getElementById("id_materiales-TOTAL_FORMS");
    const botonAgregar = document.getElementById("agregar-material");

    function ocultarFila(fila) {
        fila.hidden = true;
        fila.querySelectorAll("select, input[type='number']")
            .forEach(function (campo) {
                campo.disabled = true;
                if (campo.tomselect) {
                    campo.tomselect.disable();
                }
            });
    }

    function prepararFilas(contenedor) {
        contenedor.querySelectorAll(".fila-material")
            .forEach(function (fila) {
                const casilla = fila.querySelector(
                    'input[name$="-DELETE"]'
                );
                casilla.closest("p").hidden = true;
                if (casilla.checked) {
                    ocultarFila(fila);
                    return;
                }
                const selector = fila.querySelector(".selector-materia");
                new TomSelect(selector, { create: false });
                const botonQuitar = document.createElement("button");
                botonQuitar.type = "button";
                botonQuitar.textContent = "Quitar material";
                botonQuitar.className = "formulario-boton formulario-boton-secundario";
                botonQuitar.addEventListener("click", function () {
                    casilla.checked = true;
                    ocultarFila(fila);
                });
                fila.appendChild(botonQuitar);
            });
    }

    prepararFilas(lista);
    botonAgregar.addEventListener("click", function () {
        const nuevaFila = document.createElement("div");
        nuevaFila.innerHTML = plantilla.innerHTML.replaceAll(
            "__prefix__",
            total.value
        );
        lista.appendChild(nuevaFila);
        total.value = Number(total.value) + 1;
        prepararFilas(nuevaFila);
    });
});