import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import bannerTienda from "../assets/Portada.png";
import { toast } from "react-toastify";

const formatoPrecio = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

export const ProductoListar = () => {
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState("");
  const [categorias, setCategorias] = useState([]);
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState(null);
  const [errorCategorias, setErrorCategorias] = useState("");

  useEffect(() => {
    axios
      .get("/api/productos/")
      .then((response) => {
        setProductos(response.data);
      })
      .catch((error) => {
        console.error(error);
        setErrorCarga("No se Pudieron Cargar los Productos.");
      })
      .finally(() => {
        setCargando(false);
      });
  }, []);

  useEffect(() => {
    api
      .get("categorias/")
      .then((response) => {
        setCategorias(response.data);
      })
      .catch((error) => {
        console.error(error);
        setErrorCategorias("No se Pudieron Cargar las Categorías.");
      });
  }, []);

  const productosFiltrados = categoriaSeleccionada
  ? productos.filter(
      (producto) => producto.categoria === categoriaSeleccionada.id
    ): productos;

  const agregarAlCarrito = (id) => {
    axios.post("/api/carrito/", { producto_id: id, cantidad: 1 })
      .then(() => toast.success("producto se añadio al carrito"))
      .catch((error) => toast.error(error.response?.data?.error || "Error al agregar"));
  };

  return (
    <section>
      <div className="catalogo-banner mb-4 mb-md-5">
        <img
          src={bannerTienda}
          alt="Conejos tejidos, muñeco Freddie y llaveros de cactus"
          className="catalogo-banner-imagen"
        />
      </div>
      <div className="mb-4 mb-md-5">
        <h2 className="h5 fw-bold text-center mb-4">Explora por categoría</h2>
        {errorCategorias ? (
          <p className="text-center text-danger">
            {errorCategorias}
          </p>
        ) : (
          <div className="row row-cols-2 row-cols-md-4 g-4 justify-content-center">
            {categorias.map((categoria) => (
              <div className="col" key={categoria.id}>
                <button
                  type="button"
                  className={
                    categoriaSeleccionada?.id === categoria.id
                      ? "categoria-boton seleccionada"
                      : "categoria-boton"
                  }
                  onClick={() => setCategoriaSeleccionada(categoria)}
                >
                  <span className="categoria-foto">
                    {categoria.imagen ? (
                      <img
                        src={categoria.imagen}
                        alt=""
                        className="categoria-imagen"
                        loading="lazy"
                      />
                    ) : (
                      <span className="categoria-sin-imagen">
                        Sin Imagen
                      </span>
                    )}
                  </span>

                  <span className="categoria-nombre">
                    {categoria.nombre}
                  </span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

<div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
  <h1 className="h4 fw-bold mb-0">
    {categoriaSeleccionada
      ? categoriaSeleccionada.nombre
      : "Nuestros productos"}
  </h1>

  <button
    type="button"
    className="btn boton-secundario"
    onClick={() => setCategoriaSeleccionada(null)}
  >
    Ver todos
  </button>
</div>

      {cargando ? (
        <p className="text-center text-secondary py-5">Cargando Productos...</p>
      ) : errorCarga ? (
        <p className="text-center text-danger py-5">
          {errorCarga}
        </p>
      ) : productosFiltrados.length === 0 ? (
        <div className="catalogo-vacio text-center p-5">
          <h2 className="h5">
            {categoriaSeleccionada
              ? "No hay Productos de esta Categoría"
              : "Aún no hay Productos Publicados"}
          </h2>

          <p className="text-secondary mb-0">
            {categoriaSeleccionada
              ? "Selecciona otra Categoría o Presiona Ver Todos."
              : "Pronto Encontrarás Novedades Aquí."}
          </p>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-4">
          {productosFiltrados.map((prod) => (
            <div className="col" key={prod.id}>
              <article className="card producto-tarjeta h-100">
                <div className="producto-imagen-contenedor">
                  {prod.imagen ? (
                    <img
                      src={prod.imagen}
                      alt={prod.nombre}
                      className="producto-imagen"
                      loading="lazy"
                    />
                  ) : (
                    <div className="producto-sin-imagen">Sin Imagen</div>
                  )}
                </div>

                <div className="card-body d-flex flex-column p-4">
                  <div className="mb-3">
                    <span
                      className={
                        prod.stock_actual > 0
                          ? "badge producto-disponible"
                          : "badge producto-agotado"
                      }
                    >
                      {prod.stock_actual > 0
                        ? "Disponible"
                        : "Agotado"}
                    </span>
                  </div>

                  <h2 className="h5 producto-nombre">
                    {prod.nombre}
                  </h2>

                  <p className="producto-precio mb-4">
                    {formatoPrecio.format(Number(prod.precio))}
                  </p>

                  <div className="d-grid gap-2 mt-auto">
                    <Link
                      to={`/producto/${prod.id}`}
                      className="btn boton-secundario"
                    >
                      Ver Detalles
                    </Link>

                    <button
                      type="button"
                      className="btn boton-principal"
                      onClick={() => agregarAlCarrito(prod.id)}
                      disabled={prod.stock_actual <= 0}
                    >
                      {prod.stock_actual > 0
                        ? "Agregar al carrito"
                        : "Agotado"}
                    </button>
                  </div>
                </div>
              </article>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};