import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";

export const ProductoDetalles = () => {
  const { id } = useParams();
  const [producto, setProducto] = useState(null);

  useEffect(() => {
    axios.get(`/api/productos/${id}/`)
      .then((response) => setProducto(response.data))
      .catch((error) => console.log(error));
  }, [id]);

  const agregarAlCarrito = () => {
    axios.post("/api/carrito/", { producto_id: id, cantidad: 1 })
      .then(() => alert("producto se añadio al carrito"))
      .catch((error) => alert(error.response?.data?.error || "Error al agregar"));
  };

  if (!producto) return <div>Cargando detalles</div>;

  return (
    <div>
      <Link to="/">Volver al catálogo</Link>
      
      <h2>{producto.nombre}</h2>
      
      <div>
        {producto.imagen && (
          <img src={producto.imagen} alt={producto.nombre} width="250" />
        )}
        
        <div>
          <p><strong>Precio:</strong> ${producto.precio}</p>
          <p><strong>Stock Disponible:</strong> {producto.stock_actual}</p>
          <p><strong>Modalidad de Venta:</strong> {producto.modalidad_de_venta}</p>
          
          <div>
            <strong>Descripción:</strong>
            <p>{producto.descripcion}</p>
          </div>
          
          <button onClick={agregarAlCarrito} disabled={producto.stock_actual <= 0}>
            {producto.stock_actual > 0 ? "Agregar al Carrito" : "Agotado"}
          </button>
        </div>
      </div>
    </div>
  );
};