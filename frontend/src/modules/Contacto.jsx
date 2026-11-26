import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { api } from "../api/Api";
import "../styles/contacto.css";

const datosIniciales = {
  rut: "",
  telefono: "",
  nombre: "",
  correo: "",
  asunto: "",
  mensaje: "",
  es_personalizado: false,
  tipo_entrega: "",
  direccion_entrega: ""
};

export const Contacto = () => {
  const [form, setForm] = useState(datosIniciales);
  const [imagen, setImagen] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [cargandoCuenta, setCargandoCuenta] = useState(false);
  const [direccionCuenta, setDireccionCuenta] = useState('');

  useEffect(() => {
    if (!localStorage.getItem("access_token")) return;

    let activo = true;
    setCargandoCuenta(true);

    api.get("mi-cuenta/")
      .then(({ data }) => {
        if (!activo) return;

        const direccion = data.direccion || '';
        setDireccionCuenta(direccion);
        setForm((actual) => ({
          ...actual,
          rut: data.rut || '',
          telefono: data.telefono || '',
          nombre: `${data.nombre || ''} ${data.apellido || ''}`.trim(),
          correo: data.email || '',
          direccion_entrega: direccion
        }));
      })
      .catch(() => {
        if (activo) {
          toast.error(
            "No pudimos cargar los datos de tu cuenta. Puedes completarlos manualmente."
          );
        }
      })
      .finally(() => {
        if (activo) setCargandoCuenta(false);
      });

    return () => {
      activo = false;
    };
  }, []);

  const cambiarCampo = (e) => {
    const { name, value, type, checked } = e.target;

    setForm((actual) => ({
      ...actual,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const enviarConsulta = async (e) => {
    e.preventDefault();
    if (enviando || cargandoCuenta) return;

      if (form.es_personalizado) {
        if (!['retiro', 'envio'].includes(form.tipo_entrega)) {
          toast.error('Selecciona Cómo Quieres Recibir el Pedido');
          return;
        }

        if (
          form.tipo_entrega === 'envio' &&
          !form.direccion_entrega.trim()
        ) {
          toast.error('Indica la Dirección de Entrega');
          return;
        }
    }

    const formulario = e.currentTarget;
    const datos = new FormData();

    datos.append("nombre", form.nombre.trim());
    datos.append("correo", form.correo.trim());
    datos.append("asunto", form.asunto.trim());
    datos.append("mensaje", form.mensaje.trim());
    datos.append("es_personalizado", String(form.es_personalizado));
    datos.append('tipo_entrega', form.es_personalizado ? form.tipo_entrega : '');
    datos.append('direccion_entrega', form.es_personalizado && form.tipo_entrega === 'envio' ? form.direccion_entrega.trim() : '');
    datos.append('rut', form.es_personalizado ? form.rut.trim() : '');
    datos.append('telefono', form.es_personalizado ? form.telefono.trim() : '');

    if (imagen) {
      datos.append("imagen_referencia", imagen);
    }

    setEnviando(true);

    try {
      await api.post("consultas/", datos);

      toast.success("Tu Consulta fue Enviada Correctamente");

      setForm((actual) => ({
        ...datosIniciales,
        rut: actual.rut,
        telefono: actual.telefono,
        nombre: actual.nombre,
        correo: actual.correo,
        direccion_entrega: direccionCuenta
      }));

      setImagen(null);
      formulario.reset();
    } catch (error) {
      const respuesta = error.response?.data;

      const mensaje =
        respuesta && typeof respuesta === "object"
          ? Object.values(respuesta).flat().join(" ")
          : "No se Pudo Enviar la Consulta, Inténtalo Nuevamente";

      toast.error(mensaje);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="contacto">
      <header className="contacto-cabecera">
        <h1>Contacto</h1>
        <p>
          Escríbenos tus dudas o cuéntanos tu idea para un pedido personalizado.
        </p>
      </header>

      <form className="contacto-panel" onSubmit={enviarConsulta}>
        <fieldset disabled={enviando || cargandoCuenta}>
          <legend>Envía tu consulta</legend>

          {cargandoCuenta && <p>Cargando los Datos de tu Cuenta</p>}

          <div className="contacto-campos">
            <div className="contacto-campo">
              <label htmlFor="contacto-nombre">Nombre Completo</label>
              <input
                id="contacto-nombre"
                name="nombre"
                type="text"
                autoComplete="name"
                maxLength={150}
                value={form.nombre}
                onChange={cambiarCampo}
                required
              />
            </div>

            <div className="contacto-campo">
              <label htmlFor="contacto-correo">Correo Electrónico</label>
              <input
                id="contacto-correo"
                name="correo"
                type="email"
                autoComplete="email"
                maxLength={254}
                value={form.correo}
                onChange={cambiarCampo}
                required
              />
            </div>

            <div className="contacto-campo contacto-ancho">
              <label htmlFor="contacto-asunto">Asunto</label>
              <input
                id="contacto-asunto"
                name="asunto"
                type="text"
                maxLength={150}
                value={form.asunto}
                onChange={cambiarCampo}
                required
              />
            </div>

            <label className="contacto-opcion contacto-ancho">
              <input
                name="es_personalizado"
                type="checkbox"
                checked={form.es_personalizado}
                onChange={cambiarCampo}
              />
              <span>Mi Consulta es Sobre un Pedido Personalizado</span>
            </label>

            {form.es_personalizado && (
              <>
                <div className='contacto-campo contacto-ancho'>
                  <label htmlFor='contacto-entrega'>
                    ¿Cómo Quieres Recibir el Pedido?
                  </label>

                  <select
                    id='contacto-entrega'
                    name='tipo_entrega'
                    className='form-select'
                    value={form.tipo_entrega}
                    onChange={cambiarCampo}
                    required
                  >
                    <option value='' disabled>Selecciona una Opción</option>
                    <option value='retiro'>Retiro en Tienda</option>
                    <option value='envio'>Envío a Domicilio</option>
                  </select>
                </div>

                <div className='contacto-campo'>
                  <label htmlFor='contacto-rut'>RUT</label>
                  <input
                    id='contacto-rut'
                    name='rut'
                    type='text'
                    maxLength={12}
                    placeholder='12345678-5'
                    value={form.rut}
                    onChange={cambiarCampo}
                    required
                  />
                </div>

                <div className='contacto-campo'>
                  <label htmlFor='contacto-telefono'>Teléfono</label>
                  <input
                    id='contacto-telefono'
                    name='telefono'
                    type='tel'
                    autoComplete='tel'
                    maxLength={20}
                    placeholder='+56 9 1234 5678'
                    value={form.telefono}
                    onChange={cambiarCampo}
                    required
                  />
                </div>

                {form.tipo_entrega === 'envio' && (
                  <div className='contacto-campo contacto-ancho'>
                    <label htmlFor='contacto-direccion'>
                      Dirección de Entrega
                    </label>

                    <input
                      id='contacto-direccion'
                      name='direccion_entrega'
                      type='text'
                      autoComplete='street-address'
                      maxLength={200}
                      placeholder='Calle, Número, Departamento y Comuna'
                      value={form.direccion_entrega}
                      onChange={cambiarCampo}
                      required
                    />
                  </div>
                )}
              </>
            )}

            <div className="contacto-campo contacto-ancho">
              <label htmlFor="contacto-mensaje">Mensaje</label>
              <textarea
                id="contacto-mensaje"
                name="mensaje"
                rows={6}
                value={form.mensaje}
                onChange={cambiarCampo}
                required
              />
            </div>

            <div className="contacto-campo contacto-ancho">
              <label htmlFor="contacto-imagen">
                Imagen de referencia (opcional)
              </label>
              <input
                id="contacto-imagen"
                type="file"
                accept="image/*"
                onChange={(e) =>
                  setImagen(e.target.files?.[0] || null)
                }
              />
            </div>
          </div>

          <p className="contacto-aviso">
            Enviar esta consulta no genera un pedido ni un cobro.
          </p>

          <button
            type="submit"
            className="btn boton-principal"
          >
            {enviando ? "Enviando..." : "Enviar consulta"}
          </button>
        </fieldset>
      </form>
    </section>
  );
};