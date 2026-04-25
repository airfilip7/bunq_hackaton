type Props = { content: string }

export function UserMessage({ content }: Props) {
  return (
    <div className="self-end max-w-lg bg-surface-2 rounded-2xl rounded-br-sm px-4 py-2.5 text-sm text-text-primary">
      {content}
    </div>
  )
}
