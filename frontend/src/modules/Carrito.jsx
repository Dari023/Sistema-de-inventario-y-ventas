import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/Api";
import { toast } from 'react-toastify';
import "../styles/carrito.css";
export const Carrito = () => {
  const [carrito, setCarrito] = useState(null);

  const cargarCarrito = () => {
    api.get("carrito/")
      .then((response) => setCarrito(response.data))
      .catch((error) => console.log(error));
  };

  useEffect(() => {
    cargarCarrito();
  }, []);

  const actualizarCantidad = (producto_id, cantidad) => {
    api.post("carrito/", { producto_id: producto_id, cantidad: cantidad })
      .then(() => cargarCarrito())
      .catch((error) => toast.error(error.response?.data?.error || "Error al actualizar cantidad"));
  };

  const eliminarProducto = (producto_id) => {
    api.delete("carrito/", { data: { producto_id: producto_id } })
      .then(() => cargarCarrito())
      .catch((error) => toast.error(error.response?.data?.error || "Error al eliminar producto"));
  };

  const cancelarCompra = () => {
  api.delete("carrito/")
    .then((response) => {
      toast.success(response.data.mensaje);
      cargarCarrito();
    })
    .catch((error) => console.log(error));
  };
  const formatoPrecio = (valor) =>
    Number(valor).toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    });

  if (!carrito) return <div>Cargando carrito...</div>;

  return (
    <section className="carrito">
        <header className="carrito-cabecera">
          <h1>Mi carrito</h1>
          <p>Revisa tus productos antes de continuar.</p>
        </header>

        {carrito.detalles && carrito.detalles.length > 0 ? (
          <div className="carrito-contenido">
            <div className="carrito-panel">
              <h2>Productos ({carrito.detalles.length})</h2>

              <div className="carrito-columnas">
                <span>Producto</span>
                <span>Cantidad</span>
                <span>Subtotal</span>
              </div>

              <ul className="carrito-lista">
                {carrito.detalles.map((item) => (
                  <li key={item.id} className="carrito-producto">
                    <div className="carrito-producto-info">
                      {item.producto_imagen && (
                        <img
                          src={item.producto_imagen}
                          alt={item.producto_nombre}
                          className="carrito-imagen"
                        />
                      )}

                      <div className="carrito-producto-texto">
                        <h3>{item.producto_nombre}</h3>
                        <p>
                          Precio unitario: {formatoPrecio(item.precio_unitario)}
                        </p>

                        <button
                          type="button"
                          className="carrito-eliminar"
                          onClick={() => eliminarProducto(item.producto)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </div>

                    <div className="carrito-cantidad">
                      <button
                        type="button"
                        onClick={() => actualizarCantidad(item.producto, -1)}
                        disabled={item.cantidad <= 1}
                        aria-label={`Disminuir cantidad de ${item.producto_nombre}`}
                      >
                        −
                      </button>

                      <span>{item.cantidad}</span>

                      <button
                        type="button"
                        onClick={() => actualizarCantidad(item.producto, 1)}
                        aria-label={`Aumentar cantidad de ${item.producto_nombre}`}
                      >
                        +
                      </button>
                    </div>

                    <strong className="carrito-subtotal">
                      {formatoPrecio(item.subtotal)}
                    </strong>
                  </li>
                ))}
              </ul>

              <div className="carrito-acciones">
                <Link to="/catalogo" className="carrito-seguir">
                  ← Seguir comprando
                </Link>

                <button
                  type="button"
                  className="carrito-vaciar"
                  onClick={cancelarCompra}
                >
                  Vaciar carrito
                </button>
              </div>
            </div>

            <aside className="carrito-panel carrito-resumen">
              <h2>Resumen de compra</h2>

              <div className="carrito-resumen-fila">
                <span>Productos ({carrito.detalles.length})</span>
                <span>{formatoPrecio(carrito.total)}</span>
              </div>

              <div className="carrito-total">
                <span>Total</span>
                <strong>{formatoPrecio(carrito.total)}</strong>
              </div>

              <Link
                to="/checkout"
                className="btn boton-principal carrito-pagar"
              >
                Continuar al pago →
              </Link>
            </aside>
          </div>
        ) : (
          <div className="carrito-panel carrito-vacio">
            <h2>Tu carrito está vacío</h2>
            <p>Explora el catálogo y encuentra tu próximo favorito.</p>

            <Link to="/catalogo" className="btn boton-principal">
              Ir al catálogo
            </Link>
          </div>
        )}
      </section>
  );
};