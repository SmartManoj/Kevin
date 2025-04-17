import clsx from "clsx";
import React from "react";
import { IoIosArrowUp, IoIosArrowDown } from "react-icons/io";
import { IconButton } from "../shared/buttons/icon-button";

import { NavTab } from "./nav-tab";

interface ContainerProps {
  label?: React.ReactNode;
  labels?: {
    label: string | React.ReactNode;
    to: string;
    icon?: React.ReactNode;
    isBeta?: boolean;
  }[];
  children: React.ReactNode;
  className?: React.HTMLAttributes<HTMLDivElement>["className"];
}

export function Container({
  label,
  labels,
  children,
  className,
}: ContainerProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  const handleCollapse = () => {
    const workspace = document.querySelector(".workspace")?.parentElement as HTMLDivElement;
    const terminal = document.querySelector(".Terminal")?.parentElement as HTMLDivElement;
    if (workspace && terminal) {
      workspace.style.height = "100%";
      if (!isCollapsed) {
        terminal.style.height = "22.9px";
      } else {
        terminal.style.height = "50%";
      }
      setIsCollapsed(!isCollapsed);
    }
  };
  return (
    <div
      className={clsx(
        "bg-base-secondary border border-neutral-600 rounded-xl flex flex-col h-full",
        className,
      )}
    >
      {labels && (
        <div className="flex text-xs h-[36px] workspace">
          {labels.map(({ label: l, to, icon, isBeta }) => (
            <NavTab key={to} to={to} label={l} icon={icon} isBeta={isBeta} />
          ))}
        </div>
      )}
      {!labels && label && (
        <div className={"px-2 h-[36px] border-b border-neutral-600 text-xs flex items-center " + label}  >
          {label}
          {label === "Terminal" && (
            <IconButton
              onClick={handleCollapse}
              icon={isCollapsed ? <IoIosArrowUp /> : <IoIosArrowDown />}
              ariaLabel={isCollapsed ? "Open Terminal" : "Close Terminal"}
              style={{ marginLeft: "auto" }}
            />
          )}
        </div>
      )}
      <div className="overflow-auto flex-grow rounded-b-xl">{children}</div>
    </div>
  );
}
