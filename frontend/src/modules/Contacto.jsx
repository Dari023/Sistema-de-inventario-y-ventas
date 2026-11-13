import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { api } from "../api/Api";
import "../styles/contacto.css";

const datosIniciales = {
  nombre: "",
  correo: "",
  asunto: "",
  mensaje: "",
  es_personalizado: false,
};

export const Contacto = () => {
  const [form, setForm] = useState(datosIniciales);
  const [imagen, setImagen] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [cargandoCuenta, setCargandoCuenta] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) return;

    let activo = true;
    setCargandoCuenta(true);

    api.get("mi-cuenta/")
      .then(({ data }) => {
        if (!activo) return;

        setForm((actual) => ({
          ...actual,
          nombre: `${data.nombre || ""} ${data.apellido || ""}`.trim(),
          correo: data.email || "",
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

    const formulario = e.currentTarget;
    const datos = new FormData();

    datos.append("nombre", form.nombre.trim());
    datos.append("correo", form.correo.trim());
    datos.append("asunto", form.asunto.trim());
    datos.append("mensaje", form.mensaje.trim());
    datos.append("es_personalizado", String(form.es_personalizado));

    if (imagen) {
      datos.append("imagen_referencia", imagen);
    }

    setEnviando(true);

    try {
      await api.post("consultas/", datos);

      toast.success("Tu consulta fue enviada correctamente.");

      setForm((actual) => ({
        ...datosIniciales,
        nombre: actual.nombre,
        correo: actual.correo,
      }));

      setImagen(null);
      formulario.reset();
    } catch (error) {
      const respuesta = error.response?.data;

      const mensaje =
        respuesta && typeof respuesta === "object"
          ? Object.values(respuesta).flat().join(" ")
          : "No se pudo enviar la consulta. Inténtalo nuevamente.";

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

          {cargandoCuenta && <p>Cargando los datos de tu cuenta...</p>}

          <div className="contacto-campos">
            <div className="contacto-campo">
              <label htmlFor="contacto-nombre">Nombre completo</label>
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
              <label htmlFor="contacto-correo">Correo electrónico</label>
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
              <span>Mi consulta es sobre un pedido personalizado</span>
            </label>

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