import React from "react";
import hotToast from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { Feedback } from "#/api/open-hands.types";
import { useSubmitFeedback } from "#/hooks/mutation/use-submit-feedback";
import { BrandButton } from "../settings/brand-button";

const FEEDBACK_VERSION = "1.0";
const VIEWER_PAGE = "https://www.all-hands.dev/share";

interface FeedbackFormProps {
  onClose: () => void;
  polarity: "positive" | "negative";
}

export function FeedbackForm({ onClose, polarity }: FeedbackFormProps) {
  const { t } = useTranslation();
  const copiedToClipboardToast = () => {
    hotToast(t(I18nKey.FEEDBACK$PASSWORD_COPIED_MESSAGE), {
      icon: "📋",
      position: "bottom-right",
    });
  };

  const onPressToast = (password: string) => {
    navigator.clipboard.writeText(password);
    copiedToClipboardToast();
  };

  const shareFeedbackToast = (
    message: string,
    link: string,
    password: string,
  ) => {
    hotToast(
      <div className="flex flex-col gap-1">
        <span>{message}</span>
        <a
          data-testid="toast-share-url"
          className="text-blue-500 underline"
          href={link}
          target="_blank"
          rel="noreferrer"
        >
          {t(I18nKey.FEEDBACK$GO_TO_FEEDBACK)}
        </a>
      </div>,
      { duration: 10000 },
    );
  };

  const { mutate: submitFeedback, isPending } = useSubmitFeedback();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const formData = new FormData(event.currentTarget);

    const email = formData.get("email")?.toString() || "";
    localStorage.setItem("feedback-email", email);
    const permissions = (formData.get("permissions")?.toString() ||
      "private") as "private" | "public";

    const feedback: Feedback = {
      version: FEEDBACK_VERSION,
      email,
      polarity,
      permissions,
      trajectory: [],
      token: "",
    };

    submitFeedback(
      { feedback },
      {
        onSuccess: (data) => {
          const { message, feedback_id, password } = data.body; // eslint-disable-line
          const link = `${VIEWER_PAGE}?share_id=${feedback_id}`;
          shareFeedbackToast(message, link, password);
          onClose();
        },
      },
    );
  };

  const email = localStorage.getItem("feedback-email") || "";
  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 w-full">
      <label className="flex flex-col gap-2">
        <span className="text-xs text-neutral-400">
          {t(I18nKey.FEEDBACK$EMAIL_LABEL)}
        </span>
        <input
          required
          name="email"
          type="email"
          placeholder={t(I18nKey.FEEDBACK$EMAIL_PLACEHOLDER)}
          className="bg-[#27272A] px-3 py-[10px] rounded"
          defaultValue={email}
        />
      </label>

      <div className="flex gap-4 text-neutral-400">
        <label className="flex gap-2 cursor-pointer">
          <input
            name="permissions"
            value="private"
            type="radio"
          />
          {t(I18nKey.FEEDBACK$PRIVATE_LABEL)}
        </label>
        <label className="flex gap-2 cursor-pointer">
        <input
            name="permissions"
            value="public"
            type="radio"
            defaultChecked
          />
          {t(I18nKey.FEEDBACK$PUBLIC_LABEL)}
        </label>
      </div>

      <div className="flex gap-2">
        <BrandButton
          type="submit"
          variant="primary"
          className="grow"
          isDisabled={isPending}
        >
          {t(I18nKey.FEEDBACK$SHARE_LABEL)}
        </BrandButton>
        <BrandButton
          type="button"
          variant="secondary"
          className="grow"
          onClick={onClose}
          isDisabled={isPending}
        >
          {t(I18nKey.FEEDBACK$CANCEL_LABEL)}
        </BrandButton>
      </div>
    </form>
  );
}
