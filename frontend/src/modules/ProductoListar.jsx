import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

export const ProductoListar = () => {
  const [productos, setProductos] = useState([]);

  useEffect(() => {
    axios.get("/api/productos/")
      .then((response) => setProductos(response.data))
      .catch((error) => console.log(error));
  }, []);

  const agregarAlCarrito = (id) => {
    axios.post("/api/carrito/", { producto_id: id, cantidad: 1 })
      .then(() => alert("producto se añadio al carrito"))
      .catch((error) => alert(error.response?.data?.error || "Error al agregar"));
  };

  return (
    <div>
      <h2>Catálogo de Productos</h2>
      <div>
        {productos.map((prod) => (
          <div key={prod.id}>
            <h3>{prod.nombre}</h3>
            <p>Precio: ${prod.precio}</p>
            <Link to={`/producto/${prod.id}`}>Ver Detalles</Link>
            
            <button onClick={() => agregarAlCarrito(prod.id)} disabled={prod.stock_actual <= 0}>
              {prod.stock_actual > 0 ? "Agregar al Carrito" : "Agotado"}
            </button>
            <hr />
          </div>
        ))}
      </div>
    </div>
  );
};