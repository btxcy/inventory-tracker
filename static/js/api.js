export async function apiGet(path) {
    const res = await fetch(path)
    return res.json()
}

export async function apiPost(path, body, csrfToken) {
    
    const res = await fetch(path, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(body)
    })

    const data = await res.json()

    if (!res.ok) {
        throw new ApiError(res.status, data)
    }
    
    return data
    
}

export async function apiDelete(path, csrfToken) {

    const res = await fetch(path, {
        method: "DELETE",
        headers: {
            "X-CSRFToken": csrfToken,
        },
    })

    if (!res.ok) {
        throw new ApiError(res.status, await res.json())
    }

}   

export class ApiError extends Error {
    constructor(status, data) {
        super(data.detail || `Request failed: ${status}`)
        this.status = status
        this.data = data
    }
}