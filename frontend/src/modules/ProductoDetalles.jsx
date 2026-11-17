import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/Api";
import { toast } from 'react-toastify';
import { ResenasProducto } from "./Resenas";
export const ProductoDetalles = () => {
  const { id } = useParams();
  const [producto, setProducto] = useState(null);
  const [varianteId, setVarianteId] = useState('');

  const formatoPrecio = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });

  useEffect(() => {
    setVarianteId('');
    api.get(`productos/${id}/`)
      .then((response) => setProducto(response.data))
      .catch((error) => console.log(error));
  }, [id]);


  if (!producto) return <div>Cargando Detalles</div>;

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
      .then(() => toast.success('El Producto se Añadió Correctamente al Carrito'))
      .catch((error) =>
        toast.error(error.response?.data?.error || 'Error al Agregar')
      );
  };

  return (
    <div>
      <Link to="/catalogo">Volver al Catálogo</Link>
      
      <h2>{producto.nombre}</h2>
      
      <div>
        {producto.imagen && (
          <img src={producto.imagen} alt={producto.nombre} width="250" />
        )}
        
        <div>
{tieneTallas && (
  <div>
    <label htmlFor="talla-producto">Talla</label>
    <select
      id="talla-producto"
      value={varianteId}
      onChange={(e) => setVarianteId(e.target.value)}
    >
      <option value="">Selecciona una talla</option>
      {variantes.map((v) => (
        <option key={v.id} value={v.id}>
          {v.talla}
        </option>
      ))}
    </select>
  </div>
)}

          <p>
            <strong>{tieneTallas && !variante ? "Desde: " : "Precio: "}</strong>
            {formatoPrecio.format(Number(precio))}
          </p>

          {(!tieneTallas || variante) && (
            <p>
              {stock > 0
                ? `Stock disponible: ${stock}`
                : variante?.a_pedido
                  ? "Disponible a pedido"
                  : "Agotado"}
            </p>
          )}
          <p><strong>Modalidad de Venta:</strong> {producto.modalidad_de_venta}</p>
          <div>
            <strong>Descripción:</strong>
            <p>{producto.descripcion}</p>
          </div>
          {(!tieneTallas || variante) && stock > 0 && (
            <button type='button' onClick={agregarAlCarrito}>
              Agregar al carrito
            </button>
          )}
        </div>
      </div>
      <ResenasProducto productoId={producto.id} />
    </div>
  );
};