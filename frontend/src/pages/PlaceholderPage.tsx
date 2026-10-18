interface PlaceholderPageProps {
  title: string;
  phase: string;
}

export default function PlaceholderPage({ title, phase }: PlaceholderPageProps) {
  return (
    <div className="p-8">
      <h1 className="mb-1 text-2xl font-semibold">{title}</h1>
      <div className="mt-4 rounded-xl border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-500">
        该模块计划在{phase}实现,目前尚未开发,这里不展示虚构数据。
      </div>
    </div>
  );
}
