import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/Api";
import { toast } from "react-toastify";

const formatoPrecio = new Intl.NumberFormat("es-CL", {style: "currency", currency: "CLP", maximumFractionDigits: 0});
const filtrosIniciales = {nombre: '', categoria: '', minimo: '', maximo: '', descuento: false, orden: 'nombre'};

const normalizar = (texto) =>
  texto.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function tieneStock(producto) {
  return producto.variantes?.length
    ? producto.variantes.some((variante) => variante.stock_actual > 0)
    : producto.stock_actual > 0;
}

function precioCatalogo(producto, conDescuento = true) {
  const opciones = producto.variantes?.length
    ? producto.variantes
    : [producto];

  return Math.min(...opciones.map((opcion) => Number(
    conDescuento ? (opcion.precio_final ?? opcion.precio) : opcion.precio
  )));
}

function filtrarProductos(productos, filtros) {
  const minimo = filtros.minimo === '' ? 0 : Number(filtros.minimo);
  const maximo = filtros.maximo === '' ? Infinity : Number(filtros.maximo);

  return productos.filter((producto) => {
    const precio = precioCatalogo(producto);

    return normalizar(producto.nombre).includes(normalizar(filtros.nombre))
      && (!filtros.categoria || String(producto.categoria) === filtros.categoria)
      && precio >= minimo && precio <= maximo
      && (!filtros.descuento || Number(producto.descuento_porcentaje) > 0);
  }).sort((a, b) => {
    const nombre = a.nombre.localeCompare(b.nombre, "es", {
      sensitivity: "base"
    });

    if (filtros.orden === "nombre") return nombre;

    const diferencia = precioCatalogo(a) - precioCatalogo(b);
    return (filtros.orden === "precio_desc" ? -diferencia : diferencia) || nombre;
  });
}

export const ProductoListar = () => {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState("");
  const [errorCategorias, setErrorCategorias] = useState("");
  const [filtros, setFiltros] = useState(filtrosIniciales);

  useEffect(() => {
    let vigente = true;

    Promise.allSettled([
      api.get('productos/'),
      api.get('categorias/'),
    ]).then(([resultadoProductos, resultadoCategorias]) => {
      if (!vigente) return;

      if (resultadoProductos.status === 'fulfilled') {
        setProductos(resultadoProductos.value.data);
      } else {
        setErrorCarga('No se pPudieron Cargar los Productos');
      }

      if (resultadoCategorias.status === 'fulfilled') {
        setCategorias(resultadoCategorias.value.data);
      } else {
        setErrorCategorias('No se Pudieron Cargar las Categorías');
      }

      setCargando(false);
    });

    return () => {
      vigente = false;
    };
  }, []);

  const cambiarFiltro = ({ target }) => {
    setFiltros((actual) => ({
      ...actual,
      [target.name]: target.type === "checkbox" ? target.checked : target.value
    }));
  };

  const rangoInvalido = filtros.minimo !== "" && filtros.maximo !== ""
    && Number(filtros.minimo) > Number(filtros.maximo);

  const resultados = filtrarProductos(productos, filtros);
  const categoriaSeleccionada = categorias.find(
    (categoria) => String(categoria.id) === filtros.categoria
  );

  const agregarAlCarrito = (id) => {
    api.post("carrito/", { producto_id: id, cantidad: 1 })
      .then(() => {
        toast.success("El Producto se Añadió al Carrito");
        window.dispatchEvent(new Event("carrito-actualizado"));
      })
      .catch((error) =>
        toast.error(error.response?.data?.error || "Error al Agregar")
      );
  };

  return (
    <section>
      <header className="mb-4">
        <h1 className="mb-2">CATÁLOGO DE PRODUCTOS</h1>
        <p className="text-secondary mb-0">Explora Nuestras Categorías y Encuentra tus Favoritos</p>
      </header>

      <div className="mb-4 mb-md-5">
        <h2 className="h5 fw-bold text-center mb-4">Explora por Categoría</h2>

        {errorCategorias ? (
          <p className="text-center text-danger">{errorCategorias}</p>
        ) : (
          <div className="row row-cols-2 row-cols-md-4 g-4 justify-content-center">
            {categorias.map((categoria) => {
              const seleccionada = filtros.categoria === String(categoria.id);

              return (
                <div className="col" key={categoria.id}>
                  <button
                    type="button"
                    className={`categoria-boton${seleccionada ? " seleccionada" : ""}`}
                    onClick={() => setFiltros((actual) => ({
                      ...actual,
                      categoria: seleccionada ? "" : String(categoria.id),
                    }))}
                  >
                    <span className="categoria-foto">
                      {categoria.imagen ? (
                        <img src={categoria.imagen} alt="" className="categoria-imagen" loading="lazy" />
                      ) : (
                        <span className="categoria-sin-imagen">Sin Imagen</span>
                      )}
                    </span>
                    <span className="categoria-nombre">{categoria.nombre}</span>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <form className="border rounded-4 p-3 p-md-4 mb-4"
        onSubmit={(evento) => evento.preventDefault()}>
        <div className="row g-3">
          <div className="col-12 col-lg-4">
            <label htmlFor="buscar-producto" className="form-label fw-semibold">
              Buscar Producto
            </label>
            <input id="buscar-producto" name="nombre" type="search" className="form-control" value={filtros.nombre} onChange={cambiarFiltro} />
          </div>

          <div className="col-6 col-md-3 col-lg-2">
            <label htmlFor="precio-minimo" className="form-label fw-semibold">
              Desde ($)
            </label>
            <input id="precio-minimo" name="minimo" type="number"
              className="form-control" min="0" step="1" placeholder="Sin mínimo"
              value={filtros.minimo} onChange={cambiarFiltro} />
          </div>

          <div className="col-6 col-md-3 col-lg-2">
            <label htmlFor="precio-maximo" className="form-label fw-semibold">
              Hasta ($)
            </label>
            <input id="precio-maximo" name="maximo" type="number"
              className="form-control" min="0" step="1" placeholder="Sin máximo"
              value={filtros.maximo} onChange={cambiarFiltro} />
          </div>

          <div className="col-12 col-md-6 col-lg-4">
            <label htmlFor="orden-productos" className="form-label fw-semibold">
              Ordenar Por
            </label>
            <select id="orden-productos" name="orden" className="form-select"
              value={filtros.orden} onChange={cambiarFiltro}>
              <option value="nombre">Nombre: A a Z</option>
              <option value="precio_asc">Precio: Menor a Mayor</option>
              <option value="precio_desc">Precio: Mayor a Menor</option>
            </select>
          </div>
        </div>

        <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mt-3">
          <div className="form-check mb-0">
            <input id="solo-descuentos" name="descuento" type="checkbox"
              className="form-check-input" checked={filtros.descuento}
              onChange={cambiarFiltro} />
            <label htmlFor="solo-descuentos" className="form-check-label">
              Solo Productos con Descuento
            </label>
          </div>

          <button type="button" className="btn boton-secundario" onClick={() => setFiltros(filtrosIniciales)}>
            Limpiar Filtros
          </button>
        </div>
      </form>

      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h2 className="h4 fw-bold mb-0">
          {categoriaSeleccionada?.nombre || "Nuestros productos"}
        </h2>
        {!cargando && !errorCarga && !rangoInvalido && (
          <span className="text-secondary">
            {resultados.length} {resultados.length === 1 ? "producto" : "productos"}
          </span>
        )}
      </div>

      {cargando ? (
        <p className="text-center text-secondary py-5">Cargando Productos</p>
      ) : errorCarga ? (
        <p className="text-center text-danger py-5">{errorCarga}</p>
      ) : rangoInvalido ? (
        <p className="alert alert-warning">El Precio Mínimo no Puede Superar el Precio Máximo</p>
      ) : resultados.length === 0 ? (
        <div className="catalogo-vacio text-center p-5">
          <h3 className="h5">No Encontramos Coincidencias</h3>
          <p className="text-secondary mb-0">Prueba con Otro Nombre, Modifica los Filtros o Presiona Limpiar Filtros</p>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-4">
          {resultados.map((prod) => {
            const disponible = tieneStock(prod);
            const tieneTallas = prod.variantes?.length > 0;

            return (
              <div className="col" key={prod.id}>
                <article className="card producto-tarjeta h-100">
                  <div className="producto-imagen-contenedor">
                    {prod.imagen ? (
                      <img src={prod.imagen} alt={prod.nombre} className="producto-imagen" loading="lazy" />
                    ) : (
                      <div className="producto-sin-imagen">Sin Imagen</div>
                    )}
                  </div>

                  <div className="card-body d-flex flex-column p-4">
                    <div className="mb-3">
                      <span className={`badge ${
                        disponible ? "producto-disponible" : "producto-agotado"
                      }`}>
                        {disponible ? "Disponible" : "Agotado"}
                      </span>
                    </div>

                    <h3 className="h5 producto-nombre">{prod.nombre}</h3>

                    <p className="mb-3">
                      {tieneTallas && (
                        <small className="text-secondary me-2">Desde</small>
                      )}
                      {prod.descuento_porcentaje > 0 && (
                        <del className="text-secondary small me-2">
                          {formatoPrecio.format(precioCatalogo(prod, false))}
                        </del>
                      )}
                      <strong>
                        {formatoPrecio.format(precioCatalogo(prod))}
                      </strong>
                      {prod.descuento_porcentaje > 0 && (
                        <small className="ms-2">−{prod.descuento_porcentaje} %</small>
                      )}
                    </p>

                    <div className="d-grid gap-2 mt-auto">
                      <Link to={`/producto/${prod.id}`} className="btn boton-secundario">
                        Ver Detalles
                      </Link>

                      {tieneTallas ? (
                        <Link to={`/producto/${prod.id}`} className="btn boton-principal">
                          Elegir Talla
                        </Link>
                      ) : (
                        <button type="button" className="btn boton-principal" onClick={() => agregarAlCarrito(prod.id)} disabled={!disponible}>
                          {disponible ? "Agregar al carrito" : "Agotado"}
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};