import time


def delete_project_and_confirm(
    api,
    project_id,
    project_name,
    *,
    attempts=30,
    delay=1,
    sleep=time.sleep,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    delete_error = None
    try:
        api.delete(f"/projects/{project_id}")
    except Exception as error:
        delete_error = error

    remaining = []
    for attempt in range(attempts):
        remaining = [
            project
            for project in api.get("/projects")
            if project.get("project_id") == project_id
            or project.get("name") == project_name
        ]
        if not remaining:
            if delete_error is not None:
                print(
                    f"deletion returned {type(delete_error).__name__}, but absence "
                    f"was confirmed: {project_name}"
                )
            return
        if attempt + 1 < attempts:
            sleep(delay)

    message = f"temporary GNS3 project still exists after deletion: {project_name!r}"
    if delete_error is not None:
        raise RuntimeError(message) from delete_error
    raise RuntimeError(message)
