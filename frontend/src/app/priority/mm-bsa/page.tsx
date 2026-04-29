'use client'

import { useRouter } from 'next/navigation'

export default function MMBSAHome() {
  const router = useRouter()

  return (
    <div className="flex flex-col items-center justify-center h-[80vh] gap-8 
    bg-[#F8FAFC] dark:bg-[#050505] px-4">

      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
        E2E Checks
      </h1>

      {/* LIST VIEW */}
      <div className="flex flex-col gap-4 w-full max-w-md">

        {/* MM Checks */}
        <div
          onClick={() => router.push('/priority/mm-bsa/mm-checks')}
          className="
            cursor-pointer w-full px-6 py-4 rounded-xl shadow-md 
            bg-gradient-to-r from-blue-600 to-indigo-600 
            text-white text-base font-medium
            hover:scale-[1.02] hover:shadow-lg transition-all duration-200
            text-center
          "
        >
          MM Checks
        </div>

        {/* MM Exclusive */}
        <div
          onClick={() => router.push('/priority/mm-bsa/exclusive')}
          className="
            cursor-pointer w-full px-6 py-4 rounded-xl shadow-md 
            bg-gradient-to-r from-green-600 to-emerald-600 
            text-white text-base font-medium
            hover:scale-[1.02] hover:shadow-lg transition-all duration-200
            text-center
          "
        >
          MM Exclusive Check
        </div>

      </div>
    </div>
  )
}