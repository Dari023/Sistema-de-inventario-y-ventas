import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";

const CAMPOS = [
  ["nombre_invitado", "Nombre completo", "text"],
  ["rut_invitado", "RUT", "text"],
  ["email_invitado", "Correo electrónico", "email"],
  ["telefono_invitado", "Teléfono", "tel"],
];

const formInicial = Object.fromEntries(CAMPOS.map(([name]) => [name, ""]));

export const Checkout = () => {
  const [carrito, setCarrito] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [form, setForm] = useState(formInicial);
  const token = localStorage.getItem("access_token");
  const navigate = useNavigate();
  const [tipoEntrega, setTipoEntrega] = useState("retiro");
  const [direccion, setDireccion] = useState("");
  const [aceptaTerminos, setAceptaTerminos] = useState(false);

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
    if (!aceptaTerminos) {
      toast.error("Debes aceptar los términos y condiciones");
      return;
    }
    let payload = { tipo_entrega: tipoEntrega };
    if (!token) {
      const faltantes = CAMPOS.filter(([name]) => !form[name].trim()).map(
        ([, label]) => label
      );
      if (faltantes.length) {
        toast.error(`Completa: ${faltantes.join(", ")}`);
        return;
      }
      payload = {
        ...payload,
        ...Object.fromEntries(
          Object.entries(form).map(([k, v]) => [k, v.trim()])
        ),
      };
    }

    if (tipoEntrega === "envio") {
      if (!direccion.trim()) {
        toast.error("Ingresa la dirección de envío");
        return;
      }
      payload.direccion_invitado = direccion.trim();
    }

    setEnviando(true);
    try {
      const { data } = await api.post("webpay/iniciar/", payload);
      const formWebpay = document.createElement("form");
      formWebpay.method = "POST";
      formWebpay.action = data.url;
      const inputToken = document.createElement("input");
      inputToken.type = "hidden";
      inputToken.name = "token_ws";
      inputToken.value = data.token;
      formWebpay.appendChild(inputToken);
      document.body.appendChild(formWebpay);
      formWebpay.submit();
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
      <section>
        <h4>Tipo de entrega</h4>
        <label>
          <input
            type="radio"
            name="tipo_entrega"
            value="retiro"
            checked={tipoEntrega === "retiro"}
            onChange={() => setTipoEntrega("retiro")}
            disabled={enviando}
          />{" "}
          Retiro en tienda
        </label>
        <br />
        <label>
          <input
            type="radio"
            name="tipo_entrega"
            value="envio"
            checked={tipoEntrega === "envio"}
            onChange={() => setTipoEntrega("envio")}
            disabled={enviando}
          />{" "}
          Envío a domicilio
        </label>

        {tipoEntrega === "envio" && (
          <div style={{ marginTop: "0.5rem" }}>
            <label>
              Dirección de envío:{" "}
              <input
                type="text"
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
                disabled={enviando}
                required
              />
            </label>
          </div>
        )}
      </section>
      <label style={{ display: "block", margin: "1rem 0" }}>
        <input
          type="checkbox"
          checked={aceptaTerminos}
          onChange={(e) => setAceptaTerminos(e.target.checked)}
          disabled={enviando}
        />{" "}
        Acepto los términos y condiciones y el tratamiento de datos
      </label>
      <button type="submit" disabled={enviando}>
        {enviando ? "Redirigiendo a Webpay..." : "Pagar con Webpay"}
      </button>
    </form>
  );
};