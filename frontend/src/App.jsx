import { Routes, Route, Link } from "react-router-dom";
import { ProductoListar } from "./modules/ProductoListar";
import { ProductoDetalles } from "./modules/ProductoDetalles";
import { Carrito } from "./modules/Carrito";

export const App = () => {
  return (
    <div>
      <h1>Sistema de Inventario y Ventas</h1>
      <nav>
        <Link to="/">Productos</Link> | <Link to="/carrito">Carrito</Link>
      </nav>
      <hr />
      
      
      <Routes>
        <Route path="/" element={<ProductoListar />} />
        <Route path="/producto/:id" element={<ProductoDetalles />} />
        <Route path="/carrito" element={<Carrito />} />
      </Routes>
      
    </div>
  );
};