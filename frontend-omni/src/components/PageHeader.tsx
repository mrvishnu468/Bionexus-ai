interface PageHeaderProps {
  kicker?: string;
  title: string;
  description: string;
}

export function PageHeader({ kicker, title, description }: PageHeaderProps) {
  return (
    <header className="page-header">
      {kicker ? <p className="page-kicker">{kicker}</p> : null}
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}
