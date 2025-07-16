from fastapi import APIRouter, Request

from loguru import logger


router = APIRouter()

@router.get("/example")
def read_example(request: Request):
    webhook_url = str(request.url_for("outlook_notify")).replace('http://', 'https://')
    logger.info(f"This is outlook notify router: {webhook_url}")
    return {"message": f"This is an example router: {webhook_url}"}
