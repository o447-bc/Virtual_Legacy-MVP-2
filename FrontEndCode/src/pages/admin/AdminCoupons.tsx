import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Ticket } from "lucide-react";

interface CouponInfo {
  code: string;
  type: string;
  discount: string;
  duration: string;
  audience: string;
  delivery: string;
}

const COUPONS: CouponInfo[] = [
  {
    code: "COMEBACK20",
    type: "Percentage",
    discount: "20% off",
    duration: "3 months",
    audience: "Free users who visit /pricing a second time without subscribing",
    delivery: "Auto-displayed as amber banner on return visit",
  },
  {
    code: "LiveInDidcotFree",
    type: "Forever free",
    discount: "Lifetime Vault",
    duration: "Permanent",
    audience: "Family members (manual distribution)",
    delivery: "Enter on /pricing — instant lifetime access, no Stripe",
  },
  {
    code: "TRY14",
    type: "Time-limited",
    discount: "Free Personal",
    duration: "14 days",
    audience: "Launch campaign (manual distribution)",
    delivery: "Enter on /pricing",
  },
  {
    code: "SENIORLIVING30",
    type: "Time-limited",
    discount: "Free Family",
    duration: "30 days",
    audience: "Retirement community partnership",
    delivery: "Enter on /pricing",
  },
  {
    code: "HALFOFF3",
    type: "Percentage",
    discount: "50% off",
    duration: "3 months",
    audience: "Social media campaign (manual distribution)",
    delivery: "Enter on /pricing",
  },
  {
    code: "WINBACK-*",
    type: "Percentage",
    discount: "50% off",
    duration: "1 month",
    audience: "Users whose trial expired 3–4 days ago",
    delivery: "Auto-generated and emailed by WinBackFunction daily",
  },
];

const typeBadgeColor: Record<string, string> = {
  Percentage: "bg-blue-100 text-blue-800",
  "Forever free": "bg-green-100 text-green-800",
  "Time-limited": "bg-amber-100 text-amber-800",
};

const AdminCoupons: React.FC = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Ticket className="h-6 w-6 text-legacy-purple" />
        <h1 className="text-2xl font-bold text-legacy-navy">Coupons</h1>
      </div>

      <p className="text-sm text-gray-600 max-w-2xl">
        All active coupon codes in the system. Coupons are stored in SSM Parameter Store
        at <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">/soulreel/coupons/&#123;CODE&#125;</code>.
        Percentage coupons also need a matching Stripe Coupon in the Stripe Dashboard.
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Active Coupons</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-legacy-navy text-white">
                  <th className="px-4 py-3 text-left font-medium">Code</th>
                  <th className="px-4 py-3 text-left font-medium">Type</th>
                  <th className="px-4 py-3 text-left font-medium">Discount</th>
                  <th className="px-4 py-3 text-left font-medium">Duration</th>
                  <th className="px-4 py-3 text-left font-medium">Audience</th>
                  <th className="px-4 py-3 text-left font-medium">Delivery</th>
                </tr>
              </thead>
              <tbody>
                {COUPONS.map((coupon, idx) => (
                  <tr
                    key={coupon.code}
                    className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                  >
                    <td className="px-4 py-3 font-mono font-semibold text-legacy-purple">
                      {coupon.code}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={typeBadgeColor[coupon.type] ?? "bg-gray-100 text-gray-800"}>
                        {coupon.type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-medium">{coupon.discount}</td>
                    <td className="px-4 py-3 text-gray-600">{coupon.duration}</td>
                    <td className="px-4 py-3 text-gray-600">{coupon.audience}</td>
                    <td className="px-4 py-3 text-gray-600">{coupon.delivery}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminCoupons;
