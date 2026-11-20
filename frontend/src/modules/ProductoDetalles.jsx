import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";
import { toast } from 'react-toastify';
import { ResenasProducto } from "./Resenas";
import "../styles/ProductoDetalles.css";

const formatoPrecio = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

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

  if (!producto) {return <p role='status'>Cargando detalles…</p>;}

  const variantes = producto.variantes ?? [];
  const tieneTallas = variantes.length > 0;
  const variante = variantes.find((v) => String(v.id) === varianteId);
  const precio = variante ? (variante.precio_final ?? variante.precio) : (producto.precio_final ?? producto.precio);
  const stock = variante?.stock_actual ?? producto.stock_actual;
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
      </nav>
      <div className="detalle-contenido">
        <div className="detalle-imagen-contenedor">
          {producto.imagen ? (
            <img src={producto.imagen} alt={producto.nombre} className="detalle-imagen"/>
          ) : (
            <p>Imagen no disponible</p>
          )}
        </div>
      <div className="detalle-informacion">
        <h1>{producto.nombre}</h1>
          {tieneTallas && (
            <div>
              <label htmlFor="talla-producto">Talla</label>
              <select id="talla-producto" value={varianteId} onChange={(e) => setVarianteId(e.target.value)}>
                <option value="">Selecciona una Talla</option>
                {variantes.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.talla}
                  </option>
                ))}
              </select>
            </div>
          )}

          <p className="detalle-precio">
            <span className="detalle-precio-etiqueta">
              {tieneTallas && !variante ? "Desde" : "Precio:          "}
            </span>
            <strong>{formatoPrecio.format(Number(precio))}</strong>
          </p>

          {(!tieneTallas || variante) && (
            <div className="detalle-talla">
              <label htmlFor="talla-producto">Talla</label>
              <select
                id="talla-producto"
                value={varianteId}
                onChange={(e) => setVarianteId(e.target.value)}>
                <option value="">Selecciona una talla</option>
                {variantes.map((v) => (
                  <option key={v.id} value={v.id}> {v.talla} </option>
                ))}
              </select>
            </div>
          )}
          <p><strong>Modalidad de Venta:</strong> {producto.modalidad_de_venta}</p>
          <div>
            <strong>Descripción:</strong>
            <p>{producto.descripcion}</p>
          </div>
          {producto.admite_personalizacion && (
            <div className="detalle-personalizacion">
              <h2>Personaliza este producto</h2>
              <p>
                ¿Te gustaría este producto en otro color o con un diseño diferente?
                Cuéntanos tu idea y te responderemos a la brevedad.
              </p>
              <Link to="/contacto" className="btn boton-secundario">Consultar Personalización</Link>
            </div>
          )}
          {(!tieneTallas || variante) && stock > 0 && (
            <button type='button' onClick={agregarAlCarrito} className="btn boton-principal detalle-boton-carrito">
              Agregar al carrito
            </button>
          )}
        </div>
      </div>
      <ResenasProducto productoId={producto.id} />
    </div>
  );
};