import { Button } from "@heroui/react";
import React, { ReactElement } from "react";

export interface IconButtonProps {
  icon: ReactElement;
  onClick: () => void;
  ariaLabel: string;
  testId?: string;
  style?: React.CSSProperties;
}

export function IconButton({
  icon,
  onClick,
  ariaLabel,
  testId = "",
  style = {},
}: IconButtonProps): React.ReactElement {
  return (
    <Button
      type="button"
      variant="flat"
      onPress={onClick}
      className="cursor-pointer text-[12px] bg-transparent aspect-square px-0 min-w-[20px] h-[20px]"
      aria-label={ariaLabel}
      data-testid={testId}
      style={style}
    >
      {icon}
    </Button>
  );
}
