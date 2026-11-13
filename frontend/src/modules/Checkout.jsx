import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";
import { api } from "../api/Api";
import "../styles/checkout.css";

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
      payload.total_esperado = Number(carrito.total);
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
      formWebpay.submit()
    } catch (error) {
      toast.error(error.response?.data?.error || "Error al pagar");
      setEnviando(false)
    }
  };
  const formatoPrecio = (valor) =>
    Number(valor).toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    });

  if (!carrito) return <p>Cargando...</p>;

  return (
    <form className="checkout" onSubmit={confirmar}>
      <header className="checkout-cabecera">
        <Link to="/carrito" className="checkout-volver">
          ← Volver al carrito
        </Link>

        <h1>Finalizar compra</h1>
        <p>Completa tus datos y elige cómo recibir tu pedido.</p>
      </header>

      <div className="checkout-contenido">
        <div className="checkout-datos">
          <section className="checkout-panel">
            <h2>Datos para la compra</h2>

            {token ? (
              <p className="checkout-cuenta">
                Usaremos los datos de tu cuenta. Puedes editarlos en{" "}
                <Link to="/mi-cuenta">Mi Cuenta</Link>.
              </p>
            ) : (
              <div className="checkout-campos">
                {CAMPOS.map(([name, label, type]) => (
                  <div key={name} className="checkout-campo">
                    <label htmlFor={`checkout-${name}`}>
                      {label}
                    </label>

                    <input
                      id={`checkout-${name}`}
                      type={type}
                      name={name}
                      value={form[name]}
                      onChange={onFormChange}
                      disabled={enviando}
                    />
                  </div>
                ))}
              </div>
            )}
          </section>

          <section
            className="checkout-panel"
            aria-labelledby="checkout-entrega-titulo"
          >
            <h2 id="checkout-entrega-titulo">Tipo de entrega</h2>

            <div className="checkout-entregas">
              <label
                className={`checkout-opcion ${
                  tipoEntrega === "retiro" ? "seleccionada" : ""
                }`}
              >
                <input
                  type="radio"
                  name="tipo_entrega"
                  value="retiro"
                  checked={tipoEntrega === "retiro"}
                  onChange={() => setTipoEntrega("retiro")}
                  disabled={enviando}
                />

                <span>Retiro en tienda</span>
              </label>

              <label
                className={`checkout-opcion ${
                  tipoEntrega === "envio" ? "seleccionada" : ""
                }`}
              >
                <input
                  type="radio"
                  name="tipo_entrega"
                  value="envio"
                  checked={tipoEntrega === "envio"}
                  onChange={() => setTipoEntrega("envio")}
                  disabled={enviando}
                />

                <span>Envío a domicilio</span>
              </label>
            </div>

            {tipoEntrega === "envio" && (
              <div className="checkout-campo checkout-direccion">
                <label htmlFor="checkout-direccion">
                  Dirección de envío
                </label>

                <input
                  id="checkout-direccion"
                  type="text"
                  value={direccion}
                  onChange={(e) => setDireccion(e.target.value)}
                  disabled={enviando}
                  placeholder="Calle, número, departamento o casa"
                  required
                />
              </div>
            )}
          </section>
        </div>

        <aside className="checkout-panel checkout-resumen">
          <h2>Resumen del pedido</h2>

          <ul className="checkout-productos">
            {carrito.detalles.map((item) => (
              <li key={item.id} className="checkout-producto">
                {item.producto_imagen && (
                  <img
                    src={item.producto_imagen}
                    alt={item.producto_nombre}
                    className="checkout-imagen"
                  />
                )}

                <div className="checkout-producto-info">
                  <h3>{item.producto_nombre}</h3>
                  <p>Cantidad: {item.cantidad}</p>
                </div>

                <strong className="checkout-subtotal">
                  {formatoPrecio(item.subtotal)}
                </strong>
              </li>
            ))}
          </ul>

          <div className="checkout-total">
            <span>Total</span>
            <strong>{formatoPrecio(carrito.total)}</strong>
          </div>

          <label className="checkout-terminos">
            <input
              type="checkbox"
              checked={aceptaTerminos}
              onChange={(e) => setAceptaTerminos(e.target.checked)}
              disabled={enviando}
            />

            <span>
              Acepto los términos y condiciones y el tratamiento de datos.
            </span>
          </label>

          <button
            type="submit"
            className="btn boton-principal checkout-pagar"
            disabled={enviando}
          >
            {enviando
              ? "Redirigiendo a Webpay..."
              : "Pagar con Webpay →"}
          </button>

          <p className="checkout-aviso">
            Serás redirigido a Webpay para realizar el pago.
          </p>
        </aside>
      </div>
    </form>
  );
};