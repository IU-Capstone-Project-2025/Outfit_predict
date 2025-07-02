import { NextRequest } from 'next/server'

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const { id } = params
  if (!id) {
    return new Response(JSON.stringify({ error: 'Invalid image id' }), { status: 400 })
  }

  // Get token from cookies
  const token = req.cookies.get('token')?.value
  if (!token) {
    return new Response(JSON.stringify({ error: 'Not authenticated' }), { status: 401 })
  }

  // Use backend URL from env (can be IP/domain)
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://0.0.0.0:8000'
  const imageUrl = `${backendUrl}/api/v1/images/${id}/file`

  // Proxy the request to the backend
  const backendRes = await fetch(imageUrl, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!backendRes.ok) {
    return new Response(await backendRes.text(), { status: backendRes.status })
  }

  // Stream the image data
  const contentType = backendRes.headers.get('content-type') || 'application/octet-stream'
  return new Response(backendRes.body, {
    status: 200,
    headers: {
      'Content-Type': contentType,
    },
  })
} 