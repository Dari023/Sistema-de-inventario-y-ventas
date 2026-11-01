import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";

const CAMPOS = [
  ["nombre_invitado", "Nombre completo", "text"],
  ["rut_invitado", "RUT", "text"],
  ["email_invitado", "Correo electrónico", "email"],
  ["telefono_invitado", "Teléfono", "tel"],
  ["direccion_invitado", "Dirección de envío", "text"],
];

const formInicial = Object.fromEntries(CAMPOS.map(([name]) => [name, ""]));

export const Checkout = () => {
  const [carrito, setCarrito] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [form, setForm] = useState(formInicial);
  const token = localStorage.getItem("access_token");
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get("carrito/")
      .then(({ data }) => {
        if (!data.detalles?.length) return navigate("/carrito");
        setCarrito(data);
      })
      .catch(() => navigate("/carrito"));
  }, [navigate]);

  const onFormChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const confirmar = async (e) => {
    e.preventDefault();
    if (enviando) return;

    let payload = {};
    if (!token) {
      const faltantes = CAMPOS.filter(([name]) => !form[name].trim()).map(
        ([, label]) => label
      );
      if (faltantes.length) {
        toast.error(`Completa: ${faltantes.join(", ")}`);
        return;
      }
      payload = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v.trim()])
      );
    }

    setEnviando(true);
    try {
      const { data } = await api.post("carrito/pagar/", payload);
      toast.success("Compra confirmada");
      navigate(`/compra/${data.id_compra}`);
    } catch (error) {
      toast.error(error.response?.data?.error || "Error al pagar");
      setEnviando(false);
    }
  };

  if (!carrito) return <p>Cargando...</p>;

  return (
    <form onSubmit={confirmar}>
      <h2>Checkout</h2>
      <Link to="/carrito">← Volver al carrito</Link>

      {token ? (
        <section>
          <h4>Datos de envío</h4>
          <p>
            Usaremos los datos de tu cuenta. Puedes editarlos en{" "}
            <Link to="/mi-cuenta">Mi Cuenta</Link>.
          </p>
        </section>
      ) : (
        <section>
          <h4>Datos para la compra</h4>
          {CAMPOS.map(([name, label, type]) => (
            <div key={name}>
              <label>
                {label}:{" "}
                <input
                  type={type}
                  name={name}
                  value={form[name]}
                  onChange={onFormChange}
                  disabled={enviando}
                />
              </label>
            </div>
          ))}
        </section>
      )}

      <section>
        <h4>Resumen del pedido</h4>
        <ul>
          {carrito.detalles.map((item) => (
            <li key={item.id}>
              {item.cantidad} × {item.producto_nombre} — ${item.subtotal}
            </li>
          ))}
        </ul>
        <h3>Total: ${carrito.total}</h3>
      </section>

      <button type="submit" disabled={enviando}>
        {enviando ? "Procesando..." : "Confirmar pago"}
      </button>
    </form>
  );
};