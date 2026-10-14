"""Legacy notification helper: mutable state and a broad handler."""
def record_delivery(message, history=[]):
    try:
        history.append(message)
        return history
    except:
        return []
