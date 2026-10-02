import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

export const Carrito = () => {
  const [carrito, setCarrito] = useState(null);

  const cargarCarrito = () => {
    axios.get("/api/carrito/")
      .then((response) => setCarrito(response.data))
      .catch((error) => console.log(error));
  };

  useEffect(() => {
    cargarCarrito();
  }, []);

  const pagar = () => {
    axios.post("/api/carrito/pagar/")
      .then((response) => {
        alert(response.data.mensaje);
        cargarCarrito();
      })
      .catch((error) => alert(error.response?.data?.error || "Error al pagar"));
  };

  const cancelarCompra = () => {
    if (window.confirm("¿Estás seguro de vaciar el carrito?")) {
      axios.delete("/api/carrito/")
        .then((response) => {
          alert(response.data.mensaje);
          cargarCarrito();
        })
        .catch((error) => console.log(error));
    }
  };

  if (!carrito) return <div>Cargando carrito...</div>;

  return (
    <div>
      <h2>Mi Carrito</h2>
      
      {carrito.detalles && carrito.detalles.length > 0 ? (
        <div>
          <ul>
            {carrito.detalles.map((item) => (
              <li key={item.id}>
                {item.cantidad}x {item.producto_nombre} - Subtotal: ${item.subtotal}
              </li>
            ))}
          </ul>
          
          <h3>Total a Pagar: ${carrito.total}</h3>
          
          <button onClick={pagar}>Pagar Ahora</button>
          <button onClick={cancelarCompra}>Cancelar Compra</button>
        </div>
      ) : (
        <p>Tu carrito está vacío.</p>
      )}
    </div>
  );
};