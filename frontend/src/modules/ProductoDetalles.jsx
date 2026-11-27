import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";
import { toast } from 'react-toastify';
import { ResenasProducto } from "./Resenas";
import "../styles/ProductoDetalles.css";

const formatoPrecio = new Intl.NumberFormat("es-CL", {style: "currency", currency: "CLP", maximumFractionDigits: 0});

export const ProductoDetalles = () => {
  const { id } = useParams();
  const [producto, setProducto] = useState(null);
  const [varianteId, setVarianteId] = useState('');
  const [errorCarga, setErrorCarga] = useState(null);

  useEffect(() => {
    let consultaVigente = true;
    setProducto(null);
    setVarianteId("");
    setErrorCarga(null);

    api.get(`productos/${id}/`)
      .then(({ data }) => setProducto(data))
      .catch((error) => {
        setErrorCarga(
          error.response?.status === 404
            ? 'El Producto no se Encuentra Disponible'
            : 'No se Pudimos Cargar los Detalles del Producto'
        );
      });
  }, [id]);

  if (errorCarga) {
    return (
      <section>
        <h1>{errorCarga}</h1>
        <Link to='/catalogo'>Volver al catálogo</Link>
      </section>
    );
  }

  if (!producto) {return <p role='status'>Cargando Detalles</p>;}

  const variantes = producto.variantes ?? [];
  const tieneTallas = variantes.length > 0;
  const variante = variantes.find((v) => String(v.id) === varianteId);
  const opcionPrecio = variante ?? (tieneTallas
    ? variantes.reduce((menor, actual) =>
        Number(actual.precio_final ?? actual.precio)
          < Number(menor.precio_final ?? menor.precio)
          ? actual
          : menor
      )
    : producto
  );
  const precioOriginal = Number(opcionPrecio.precio);
  const precio = Number(opcionPrecio.precio_final ?? opcionPrecio.precio);
  const tieneDescuento = precio < precioOriginal;
  const stock = variante
    ? Number(variante.stock_actual)
    : tieneTallas
      ? variantes.reduce((total, v) => total + Number(v.stock_actual), 0)
      : Number(producto.stock_actual);

  const agregarAlCarrito = () => {
    if ((tieneTallas && !variante) || stock <= 0) return;

    const datos = { producto_id: id, cantidad: 1 };

    if (variante) {
      datos.variante_id = variante.id;
    }

    api.post('carrito/', datos)
      .then(() => {toast.success('El Producto se Añadió Correctamente al Carrito');
        window.dispatchEvent(new Event("carrito-actualizado"));
      })
      .catch((error) =>
        toast.error(error.response?.data?.error || 'Error al Agregar')
      );
  };

  return (
    <div className="detalle-producto">
      <nav className="detalle-ruta" aria-label="Ruta de navegación">
        <Link to="/">Inicio</Link>
        <span aria-hidden="true">/</span>
        <Link to="/catalogo">Catálogo</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{producto.nombre}</span>
        <p className="text-secondary mb-3">
          <strong>Categoría:</strong> {producto.categoria_nombre}
        </p>
      </nav>
      <div className="detalle-contenido">
        <div className="detalle-imagen-contenedor">
          {producto.imagen ? (
            <img src={producto.imagen} alt={producto.nombre} className="detalle-imagen"/>
          ) : (
            <p>Imagen no Disponible</p>
          )}
        </div>
      <div className="detalle-informacion">
        <h1>{producto.nombre}</h1>

          <p className="detalle-precio">
            <span className="detalle-precio-etiqueta">
              {tieneTallas && !variante ? "Desde" : "Precio"}
            </span>
            {tieneDescuento && (
              <del className='text-secondary'>
                {formatoPrecio.format(precioOriginal)}
              </del>
            )}
            <strong>{formatoPrecio.format((precio))}</strong>
            {tieneDescuento && (
              <span className='detalle-precio-etiqueta'>
                Precio con Descuento
              </span>
            )}
          </p>

          {tieneTallas && (
            <div className='detalle-talla'>
              <label>
                Talla: {variante ? <span>{variante.talla}</span> : <span className="fw-normal text-secondary">Selecciona una</span>}
              </label>
              <div className="d-flex flex-wrap gap-2 mt-1">
                {variantes.map((v) => {
                  const sinStock = Number(v.stock_actual) <= 0;
                  const estaSeleccionada = varianteId === String(v.id);

                  return (
                    <button
                      key={v.id}
                      type="button"
                      disabled={sinStock}
                      onClick={() => setVarianteId(String(v.id))}
                      className={`btn fw-bold rounded-3 ${estaSeleccionada
                          ? 'btn-dark'
                          : 'btn-outline-secondary'
                        } ${sinStock ? 'text-decoration-line-through' : ''}`}
                      style={{ minWidth: '3.5rem' }}
                    >
                      {v.talla}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <p>
            <strong>Disponibilidad:</strong>{' '}
            <span className={`badge ${
              stock > 0 ? 'producto-disponible' : 'producto-agotado'
            }`}>
              {stock > 0
                ? tieneTallas && !variante
                  ? 'Disponible en Algunas Tallas'
                  : 'Disponible'
                : 'Agotado'}
            </span>
          </p>

          <p><strong>Modalidad de Venta:</strong> {producto.modalidad_de_venta}</p>
          <div>
            <strong>Descripción:</strong>
            <p>{producto.descripcion}</p>
          </div>
          {(!tieneTallas || variante) && stock > 0 && (
            <button type='button' onClick={agregarAlCarrito} className="btn boton-principal detalle-boton-carrito">
              Agregar al Carrito
            </button>
          )}
        </div>
      </div>
      <ResenasProducto productoId={producto.id} />
    </div>
  );
};