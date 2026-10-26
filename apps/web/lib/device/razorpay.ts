/** Razorpay Checkout (web): loaded on demand; UPI preferred (FR-PAY-4). */

const SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

export type CheckoutSuccess = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

type RazorpayInstance = { open: () => void; on: (event: string, cb: () => void) => void };
type RazorpayCtor = new (options: Record<string, unknown>) => RazorpayInstance;

function loadScript(): Promise<RazorpayCtor> {
  const existing = (window as unknown as { Razorpay?: RazorpayCtor }).Razorpay;
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT;
    script.async = true;
    script.onload = () => {
      const ctor = (window as unknown as { Razorpay?: RazorpayCtor }).Razorpay;
      if (ctor) resolve(ctor);
      else reject(new Error("Razorpay unavailable"));
    };
    script.onerror = () => reject(new Error("Razorpay unavailable"));
    document.head.appendChild(script);
  });
}

/** Resolves with the Checkout result, or null if the user closed the sheet. */
export async function openCheckout(options: {
  keyId: string;
  orderId: string;
  amountPaise: number;
  name: string;
  description: string;
  email?: string | null;
  method: "upi" | "card";
}): Promise<CheckoutSuccess | null> {
  const Razorpay = await loadScript();
  return new Promise((resolve) => {
    const rzp = new Razorpay({
      key: options.keyId,
      order_id: options.orderId,
      amount: options.amountPaise,
      currency: "INR",
      name: options.name,
      description: options.description,
      prefill: { email: options.email ?? undefined, method: options.method },
      handler: (response: CheckoutSuccess) => resolve(response),
      modal: { ondismiss: () => resolve(null) },
    });
    rzp.open();
  });
}
