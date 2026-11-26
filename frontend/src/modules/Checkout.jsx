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
  const [cargandoCuenta, setCargandoCuenta] = useState(Boolean(token));
  const [errorCuenta, setErrorCuenta] = useState('');
  const navigate = useNavigate();
  const [tipoEntrega, setTipoEntrega] = useState("retiro");
  const [direccion, setDireccion] = useState("");
  const [aceptaTerminos, setAceptaTerminos] = useState(false);
  const [regiones, setRegiones] = useState([]);
  const [errorEnvio, setErrorEnvio] = useState('');
  const [envio, setEnvio] = useState({region: '', comuna: '', complemento: ''});

  useEffect(() => {
    api
      .get("carrito/")
      .then(({ data }) => {
        if (!data.detalles?.length) return navigate("/carrito");
        setCarrito(data);
      })
      .catch(() => navigate("/carrito"));
  }, [navigate]);

  useEffect(() => {
    if (!token) return;

    let vigente = true;
    setCargandoCuenta(true);
    setErrorCuenta('');

    api.get('mi-cuenta/')
      .then(({ data }) => {
        if (!vigente) return;

        setForm({
          nombre_invitado: `${data.nombre || ''} ${data.apellido || ''}`.trim(),
          rut_invitado: data.rut || '',
          email_invitado: data.email || '',
          telefono_invitado: data.telefono || ''
        });

        setDireccion(data.direccion || '');
      })
      .catch(() => {
        if (vigente) {
          setErrorCuenta('No Pudimos Cargar los Datos de tu Cuenta, Recarga la Página Para Reintentar');
        }
      })
      .finally(() => {
        if (vigente) setCargandoCuenta(false);
      });

    return () => {
      vigente = false;
    };
  }, [token]);

  useEffect(() => {
    let vigente = true;

    api.get('opciones-entrega/')
      .then(({ data }) => {
        if (vigente) setRegiones(data);
      })
      .catch(() => {
        if (vigente) {
          setErrorEnvio('No Pudimos Cargar las Opciones de Envío');
        }
      });

    return () => {
      vigente = false;
    };
  }, []);

  const onFormChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const confirmar = async (e) => {
    e.preventDefault();
    if (enviando || cargandoCuenta || !carrito) return;

    if (errorCuenta) {
      toast.error(errorCuenta);
      return;
    }

    if (!aceptaTerminos) {
      toast.error("Debes Aceptar los Términos y Condiciones");
      return;
    }

    const faltantes = CAMPOS
      .filter(([name]) => !form[name].trim())
      .map(([, label]) => label);

    if (faltantes.length) {
      toast.error(`Completa: ${faltantes.join(", ")}`);
      return;
    }

    const payload = {
      tipo_entrega: tipoEntrega,
      ...Object.fromEntries(
        Object.entries(form).map(([campo, valor]) => [campo, valor.trim()])
      ),
    };

    if (tipoEntrega === "envio") {
      if (!direccion.trim()) {
        toast.error("Ingresa la Dirección de Envío");
        return;
      }
      payload.direccion_invitado = direccion.trim();
    }

    if (faltaEnvio) {
      toast.error('Selecciona una Región y Comuna con Envío Disponible');
      return;
    }

    payload.codigo_region = envio.region;
    payload.codigo_comuna = envio.comuna;
    payload.complemento = envio.complemento.trim();

    setEnviando(true);
    try {
      payload.total_esperado = total;
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
      toast.error(error.response?.data?.error || "Error al Pagar");
      setEnviando(false)
    }
  };
  const formatoPrecio = (valor) =>
    Number(valor).toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    });

  if (!carrito) return <p>Cargando</p>;

  const regionSeleccionada = regiones.find((region) => region.codigo === envio.region);
  const comunaValida = regionSeleccionada?.comunas.some((comuna) => comuna.codigo === envio.comuna);
  const envioValido = Boolean(regionSeleccionada && regionSeleccionada.costo_envio !== null && comunaValida);
  const faltaEnvio = tipoEntrega === "envio" && !envioValido;
  const subtotal = Number(carrito.subtotal_productos ?? carrito.total);
  const costoEnvio = tipoEntrega === "envio" && envioValido
    ? Number(regionSeleccionada.costo_envio)
    : 0;
  const total = subtotal + costoEnvio;
  const neto = Math.round(total / 1.19);
  const ivaIncluido = total - neto;

  return (
    <form className="checkout" onSubmit={confirmar}>
      <header className="checkout-cabecera">
        <Link to="/carrito" className="checkout-volver">
          Volver al Carrito
        </Link>

        <h1>FINALIZAR COMPRA</h1>
        <p>Completa tus Datos y Elige Cómo Recibir tu Pedido</p>
      </header>

      <div className="checkout-contenido">
        <div className="checkout-datos">
          <section className="checkout-panel">
            <h2>Datos para la compra</h2>

            {token && (
              <div className="checkout-cuenta">
                <p className="mb-2">
                  Cargamos los datos de tu cuenta. Puedes ajustar los datos de
                  contacto para esta compra sin modificar tu perfil.
                </p>

                <Link to='/mi-cuenta' className='btn btn-outline-secondary btn-sm'>
                  Modificar Datos de mi Cuenta
                </Link>
              </div>
            )}

            {cargandoCuenta && (
              <p className='text-secondary'>Cargando los Datos de tu Cuenta</p>
            )}

            {errorCuenta && (
              <p className='alert alert-danger'>{errorCuenta}</p>
            )}

            <div className='checkout-campos'>
              {CAMPOS.map(([name, label, type]) => (
                <div key={name} className='checkout-campo'>
                  <label htmlFor={`checkout-${name}`}>{label}</label>

                  <input
                    id={`checkout-${name}`}
                    type={type}
                    name={name}
                    value={form[name]}
                    onChange={onFormChange}
                    readOnly={Boolean(token) && name === 'rut_invitado'}
                    disabled={enviando || cargandoCuenta || Boolean(errorCuenta)}
                    required
                  />
                </div>
              ))}
            </div>
          </section>

          <section className="checkout-panel">
            <h2 id="checkout-entrega-titulo">Tipo de Entrega</h2>

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

                <span>Retiro en Tienda</span>
              </label>

              <label className={`checkout-opcion ${
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

                <span>Envío a Domicilio</span>
              </label>
            </div>

            {tipoEntrega === "envio" && (
              <div className="checkout-direccion">
                {errorEnvio && (
                  <p className="alert alert-danger">{errorEnvio}</p>
                )}

                <div className='checkout-campos'>
                  <div className='checkout-campo'>
                    <label htmlFor='checkout-region'>Región</label>
                    <select
                      id='checkout-region'
                      className='form-select'
                      value={envio.region}
                      onChange={(e) => setEnvio({
                        ...envio,
                        region: e.target.value,
                        comuna: ''
                      })}
                      disabled={enviando || !regiones.length}
                      required
                    >
                      <option value=''>Selecciona una Región</option>
                      {regiones.map((region) => (
                        <option key={region.codigo} value={region.codigo} disabled={region.costo_envio === null}>
                          {region.nombre}
                          {region.costo_envio === null ? ' — Sin Envío Disponible' : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className='checkout-campo'>
                    <label htmlFor='checkout-comuna'>Comuna</label>
                    <select
                      id='checkout-comuna'
                      className='form-select'
                      value={envio.comuna}
                      onChange={(e) => setEnvio({ ...envio, comuna: e.target.value })}
                      disabled={enviando || !regionSeleccionada}
                      required
                    >
                      <option value=''>Selecciona una Comuna</option>
                      {(regionSeleccionada?.comunas ?? []).map((comuna) => (
                        <option key={comuna.codigo} value={comuna.codigo}>
                          {comuna.nombre}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className='checkout-campo'>
                    <label htmlFor='checkout-direccion'>Calle y Número</label>
                    <input
                      id='checkout-direccion'
                      type='text'
                      value={direccion}
                      onChange={(e) => setDireccion(e.target.value)}
                      disabled={enviando || cargandoCuenta || Boolean(errorCuenta)}
                      placeholder='Ej.: Las Acacias 123'
                      maxLength={200}
                      required
                    />
                  </div>

                  <div className='checkout-campo'>
                    <label htmlFor='checkout-complemento'>
                      Departamento, casa u otra referencia (opcional)
                    </label>
                    <input
                      id='checkout-complemento'
                      type='text'
                      value={envio.complemento}
                      onChange={(e) => setEnvio({
                        ...envio,
                        complemento: e.target.value,
                      })}
                      disabled={enviando}
                      maxLength={50}
                    />
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        <aside className="checkout-panel checkout-resumen">
          <h2>Resumen del Pedido</h2>

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

          <div className='border-top pt-3'>
            <div className='d-flex justify-content-between gap-3 mb-2'>
              <span>Productos</span>
              <span>{formatoPrecio(subtotal)}</span>
            </div>

            <div className='d-flex justify-content-between gap-3 mb-3'>
              <span>{tipoEntrega === 'envio' ? 'Envío' : 'Retiro en Tienda'}</span>
              <span>
                {faltaEnvio ? 'Selecciona Destino' : formatoPrecio(costoEnvio)}
              </span>
            </div>

            {!faltaEnvio && (
              <>
                <div className='d-flex justify-content-between gap-3 text-secondary mb-2'>
                  <span>Neto</span>
                  <span>{formatoPrecio(neto)}</span>
                </div>

                <div className='d-flex justify-content-between gap-3 text-secondary mb-2'>
                  <span>IVA Incluido (19 %)</span>
                  <span>{formatoPrecio(ivaIncluido)}</span>
                </div>
              </>
            )}

            <div className="checkout-total">
              <span>Total a Pagar</span>
              <strong>{faltaEnvio ? "Por calcular" : formatoPrecio(total)}</strong>
            </div>
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

          <button type="submit" className="btn boton-principal checkout-pagar" disabled={enviando || cargandoCuenta || Boolean(errorCuenta) || faltaEnvio}>
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