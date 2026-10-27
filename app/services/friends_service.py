from datetime import date
from typing import List
from fastapi import HTTPException
from sqlalchemy import or_, and_
from app.db.session import SessionLocal
from app.db.models import UsuarioDB, AmistadDB
from app.models.friends import Amigos, SolicitudAmistad, UsuarioPublico


def _entre(a: int, b: int):
    return or_(
        and_(AmistadDB.solicitante_id == a, AmistadDB.destinatario_id == b),
        and_(AmistadDB.solicitante_id == b, AmistadDB.destinatario_id == a),
    )


def ids_amigos(db, usuario_id: int) -> List[int]:
    filas = db.query(AmistadDB).filter(
        AmistadDB.estado == "aceptada",
        or_(AmistadDB.solicitante_id == usuario_id, AmistadDB.destinatario_id == usuario_id)
    ).all()
    return [f.destinatario_id if f.solicitante_id == usuario_id else f.solicitante_id for f in filas]


def listar(usuario_id: int) -> Amigos:
    db = SessionLocal()
    try:
        filas = db.query(AmistadDB).filter(
            or_(AmistadDB.solicitante_id == usuario_id, AmistadDB.destinatario_id == usuario_id)
        ).order_by(AmistadDB.id).all()
        otros = {f.destinatario_id if f.solicitante_id == usuario_id else f.solicitante_id for f in filas}
        nombres = {u.id: u.username for u in db.query(UsuarioDB).filter(UsuarioDB.id.in_(otros)).all()}

        amigos, recibidas, enviadas = [], [], []
        for f in filas:
            otro = f.destinatario_id if f.solicitante_id == usuario_id else f.solicitante_id
            persona = UsuarioPublico(usuario_id=otro, username=nombres.get(otro, "?"))
            if f.estado == "aceptada":
                amigos.append(persona)
            elif f.destinatario_id == usuario_id:
                recibidas.append(SolicitudAmistad(id=f.id, usuario=persona, fecha=f.fecha or ""))
            else:
                enviadas.append(SolicitudAmistad(id=f.id, usuario=persona, fecha=f.fecha or ""))
        amigos.sort(key=lambda p: p.username.lower())
        return Amigos(amigos=amigos, recibidas=recibidas, enviadas=enviadas)
    finally:
        db.close()


def enviar_solicitud(usuario_id: int, usuario_o_email: str) -> str:
    """Devuelve 'enviada' o 'aceptada' (si la otra persona ya te había enviado una)."""
    texto = usuario_o_email.strip()
    db = SessionLocal()
    try:
        destino = db.query(UsuarioDB).filter(
            or_(UsuarioDB.username == texto, UsuarioDB.email == texto)
        ).first()
        if not destino:
            raise HTTPException(status_code=404, detail="No existe ningún usuario con ese nombre o email.")
        if destino.id == usuario_id:
            raise HTTPException(status_code=400, detail="No puedes agregarte a ti mismo.")

        existente = db.query(AmistadDB).filter(_entre(usuario_id, destino.id)).first()
        if existente:
            if existente.estado == "aceptada":
                raise HTTPException(status_code=400, detail=f"{destino.username} ya es tu amigo.")
            if existente.solicitante_id == usuario_id:
                raise HTTPException(status_code=400, detail=f"Ya enviaste una solicitud a {destino.username}.")
            # Te la había enviado él/ella: se acepta directamente
            existente.estado = "aceptada"
            db.commit()
            return "aceptada"

        db.add(AmistadDB(solicitante_id=usuario_id, destinatario_id=destino.id,
                         estado="pendiente", fecha=date.today().isoformat()))
        db.commit()
        return "enviada"
    finally:
        db.close()


def aceptar_solicitud(usuario_id: int, solicitud_id: int) -> bool:
    db = SessionLocal()
    try:
        fila = db.query(AmistadDB).filter(
            AmistadDB.id == solicitud_id, AmistadDB.destinatario_id == usuario_id, AmistadDB.estado == "pendiente"
        ).first()
        if not fila:
            return False
        fila.estado = "aceptada"
        db.commit()
        return True
    finally:
        db.close()


def borrar_solicitud(usuario_id: int, solicitud_id: int) -> bool:
    """Rechazar (si la recibiste) o cancelar (si la enviaste) una solicitud pendiente."""
    db = SessionLocal()
    try:
        fila = db.query(AmistadDB).filter(
            AmistadDB.id == solicitud_id, AmistadDB.estado == "pendiente",
            or_(AmistadDB.solicitante_id == usuario_id, AmistadDB.destinatario_id == usuario_id)
        ).first()
        if not fila:
            return False
        db.delete(fila)
        db.commit()
        return True
    finally:
        db.close()


def eliminar_amigo(usuario_id: int, amigo_id: int) -> bool:
    db = SessionLocal()
    try:
        fila = db.query(AmistadDB).filter(_entre(usuario_id, amigo_id), AmistadDB.estado == "aceptada").first()
        if not fila:
            return False
        db.delete(fila)
        db.commit()
        return True
    finally:
        db.close()
