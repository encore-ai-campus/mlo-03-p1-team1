from app.core.security import utcnow
from app.schemas import ProfileInput


def update_profile(store, user, data: ProfileInput):
    values = data.model_dump(exclude_unset=True)
    if 'age' in values:
        # MariaDB DATETIME stores whole seconds; return the same value as later reads.
        values['age_recorded_at'] = utcnow().replace(microsecond=0) if values['age'] is not None else None
    return store.update_profile(user, values)
