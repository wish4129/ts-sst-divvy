import Loading from './Loading'
import { useAuth } from '../lib/AuthContext'

export default function LoginGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <Loading />

  if (!user) {
    return (
      <div className="flex items-center justify-center py-32">
        <p className="text-gray-500 text-lg">Sign in to manage your portfolio</p>
      </div>
    )
  }

  return <>{children}</>
}
