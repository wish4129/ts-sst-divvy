import Loading from './Loading'
import { useAuth } from '../lib/AuthContext'

export default function LoginGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <Loading />

  if (!user) {
    return (
      <div role="alert" className="flex items-center justify-center py-32">
        <h2 className="text-gray-500 text-lg">Sign in to manage your portfolio</h2>
      </div>
    )
  }

  return <>{children}</>
}
