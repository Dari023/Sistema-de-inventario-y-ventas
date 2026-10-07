import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { toast } from 'react-toastify';
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

  const actualizarCantidad = (producto_id, cantidad) => {
    axios.post("/api/carrito/", { producto_id: producto_id, cantidad: cantidad })
      .then(() => cargarCarrito())
      .catch((error) => toast.error(error.response?.data?.error || "Error al actualizar cantidad"));
  };

  const eliminarProducto = (producto_id) => {
    axios.delete("/api/carrito/", { data: { producto_id: producto_id } })
      .then(() => cargarCarrito())
      .catch((error) => toast.error(error.response?.data?.error || "Error al eliminar producto"));
  };

 const cancelarCompra = () => {
  axios.delete("/api/carrito/")
    .then((response) => {
      toast.success(response.data.mensaje);
      cargarCarrito();
    })
    .catch((error) => console.log(error));
  };

  if (!carrito) return <div>Cargando carrito...</div>;

  return (
    <div>
      <h2>Mi Carrito</h2>
      
      {carrito.detalles && carrito.detalles.length > 0 ? (
        <div>
          <ul>
            {carrito.detalles.map((item) => (
              <li key={item.id} style={{ marginBottom: "10px" }}>
                <button  onClick={() => actualizarCantidad(item.producto, -1)}disabled={item.cantidad <= 1}> - </button>
                <span style={{ margin: "0 10px" }}>{item.cantidad}</span>
                <button onClick={() => actualizarCantidad(item.producto, 1)}style={{ marginRight: "10px" }}> + </button>
                <button onClick={() => eliminarProducto(item.producto)}style={{ marginLeft: "15px", color: "red", cursor: "pointer" }}>x</button>
                {item.producto_nombre} - Subtotal: ${item.subtotal}
              </li>
            ))}
          </ul>

          <h3>Total a Pagar: ${carrito.total}</h3>
          
          <button onClick={pagar}>Pagar Ahora</button>
          <button onClick={cancelarCompra}>vaciar Carrito</button>
        </div>
      ) : (
        <p>Tu carrito está vacío.</p>
      )}
    </div>
  );
};