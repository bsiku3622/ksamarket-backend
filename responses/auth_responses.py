from fastapi import HTTPException


USER_NOT_FOUND = HTTPException(status_code=404, detail="User not found")
USER_IS_PENDING = HTTPException(status_code=404, detail="User is pending")
USER_IS_SUSPENDED = HTTPException(status_code=404, detail="User is suspended")
INVALID_PASSWORD = HTTPException(status_code=400, detail="Invalid password")

EMAIL_ALREADY_VERIFIED = HTTPException(status_code=400, detail="Email already verified")

SESSION_NOT_FOUND = HTTPException(status_code=404, detail="Session not found")
SESSION_EXPIRED = HTTPException(status_code=404, detail="Session expired")
