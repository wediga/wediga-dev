import CosmosBackground from "@/components/cosmos/CosmosBackground";

/**
 * Layout for the visual relaunch surface. The dark cosmos palette and the
 * animated background live here instead of the global root layout, so the
 * existing light-themed pages (public landing, login, admin, recruiter) keep
 * their plain shell while this surface gets the full dark experience.
 */
export default function DesignDemoLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="cosmos-surface flex min-h-full flex-1 flex-col">
      <CosmosBackground />
      <div className="relative z-[1] flex min-h-full flex-1 flex-col">
        {children}
      </div>
    </div>
  );
}
