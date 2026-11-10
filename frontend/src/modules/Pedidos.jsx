import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/Api";

export const Pedidos = () => {
  const [pedidos, setPedidos] = useState(null);

  useEffect(() => {
    api.get("mi-cuenta/pedidos/")
      .then((response) => setPedidos(response.data))
      .catch(() => setPedidos([]));
  }, []);

  return (
    <section>
      <h2 className="h4 mb-3">Mis Pedidos</h2>
      {pedidos === null && (<p className="text-muted">Cargando Pedidos...</p>)}
      {pedidos && pedidos.length === 0 && (<p className="text-muted">Aún no Tienes Pedidos.</p>)}
      {pedidos && pedidos.length > 0 && (
        <div className="list-group">
          {pedidos.map((p) => (
            <Link
              key={p.id}
              to={`/compra/${p.id_compra}`}
              className="list-group-item list-group-item-action d-flex justify-content-between align-items-start"
            >
              <div>
                <strong>Pedido #{p.id}</strong>
                <br />
                <small className="text-muted">
                  {new Date(p.fecha_pedido).toLocaleString("es-CL")}
                </small>
              </div>
              <div className="text-end">
                <strong>${Number(p.total).toLocaleString("es-CL")}</strong>
                <br />
                <small className="text-muted">
                  {p.detalles.length} producto{p.detalles.length === 1 ? "" : "s"}
                </small>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
};