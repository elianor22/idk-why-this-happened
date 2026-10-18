#version 430
uniform vec2 uC;
uniform float uR0;
uniform float uRd;
uniform vec4 uStr[4];      // phi0, dir, turns, unused
uniform vec4 uStrT[4];     // t0, t1, ink-id, unused
uniform vec3 uInk[4];
uniform float uGold;
uniform float uWhite;
uniform float uFadeIn;
out vec4 o;

float px;
float aa(float d, float w){ return smoothstep(w + px, w - px, d); }
float wrapA(float a){ return a - TAU * floor((a + PI) / TAU); }

vec3 paper(vec2 uv){
    float n = fbm(vec3(uv * 2.5, 0.3), 4) * 0.5;
    float f = vnoise(vec3(uv * 700.0, 1.0));
    float f2 = vnoise(vec3(uv * vec2(60.0, 900.0), 3.0));
    vec3 c = vec3(0.948, 0.928, 0.872);
    c *= 1.0 + 0.014 * n + 0.016 * (f - 0.5) + 0.010 * (f2 - 0.5);
    c *= 1.0 - 0.10 * dot(uv, uv * vec2(0.6, 1.0));
    return c;
}

float streamEase(float u){ u = clamp(u, 0.0, 1.0); return 1.0 - pow(1.0 - u, 2.0); }

void main(){
    vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    px = 1.3 / uRes.y;
    float t = uTime;
    vec2 p = uv - uC;
    float r = length(p);
    float phi = atan(p.y, p.x);
    vec3 col = paper(uv);
    vec3 inkDark = vec3(0.16, 0.17, 0.24);

    // ---- guide geometry (hairlines)
    float guide = 0.0;
    float rings[7] = float[](0.10, 0.145, 0.205, 0.265, 0.33, 0.385, uR0);
    for (int i = 0; i < 7; i++){
        float w = (i == 6) ? 0.0012 : 0.0006;
        float a = aa(abs(r - rings[i]), w) * ((i == 6) ? 0.85 : 0.30);
        guide = max(guide, a);
    }
    // ticks on the outer ring
    float ta = phi / TAU * 144.0;
    float tf = abs(fract(ta + 0.5) - 0.5) / 144.0 * TAU * r;
    float isMajor = step(abs(fract(ta / 6.0 + 0.5) - 0.5) * 6.0, 0.5);
    float tickLen = mix(0.012, 0.024, isMajor);
    float tick = aa(tf, 0.0006) * step(uR0 - tickLen, r) * step(r, uR0) * 0.8;
    float ticks2 = aa(abs(fract(ta + 0.5) - 0.5) / 144.0 * TAU * r, 0.0005) * step(uR0 + 0.004, r) * step(r, uR0 + 0.004 + 0.008 * isMajor) * 0.7;
    guide = max(guide, max(tick, ticks2));
    // radial hairlines
    float rd = abs(fract(phi / TAU * 48.0 + 0.5) - 0.5) / 48.0 * TAU * r;
    float radial = aa(rd, 0.0004) * step(uRd * 1.6, r) * step(r, 0.30) * 0.16;
    guide = max(guide, radial);
    // crosshair
    float ch = max(aa(abs(p.x), 0.0005) * step(abs(p.y), uR0 + 0.03), aa(abs(p.y), 0.0005) * step(abs(p.x), uR0 + 0.03)) * 0.35;
    guide = max(guide, ch * step(uRd * 1.3, r));
    col *= mix(vec3(1.0), inkDark, guide * 0.78 * uFadeIn);

    // ---- streams
    float smax = 1.0 - uRd / uR0;
    float discFill[4];
    for (int i = 0; i < 4; i++){
        float t0 = uStrT[i].x, t1 = uStrT[i].y;
        float u = (t - t0) / (t1 - t0);
        float sh = streamEase(u) * smax;
        float spix = 1.0 - r / uR0;
        float phiE = uStr[i].x + uStr[i].y * uStr[i].z * spix;
        float dphi = wrapA(phi - phiE);
        // wrap multi-turn ambiguity: take nearest
        float d = abs(dphi) * r;
        float len = 0.62 * smax;
        float tr = smoothstep(sh - len, sh, spix) * step(spix, sh) * step(0.0, spix);
        float wid = mix(0.0018, 0.0110, smoothstep(sh - len, sh, spix));
        float stroke = aa(d, wid) * tr;
        vec3 ink = uInk[i];
        // hairline of the full path
        float pathLine = aa(d, 0.0004) * step(0.0, spix) * step(spix, smax) * 0.30 * smoothstep(0.0, 1.0, u * 4.0 + 0.2);
        float st = max(stroke * 0.92, pathLine * 0.6);
        // head
        float sH = sh;
        float rH = uR0 * (1.0 - sH);
        float aH = uStr[i].x + uStr[i].y * uStr[i].z * sH;
        vec2 hp = rH * vec2(cos(aH), sin(aH));
        float dh = length(p - hp);
        float head = aa(dh - 0.0, 0.0140) * step(0.0, u) * step(u, 1.0 - 1e-4 + 0.0);
        float ringH = aa(abs(dh - 0.022), 0.0013) * step(0.0, u) * 0.9 * (1.0 - smoothstep(0.92, 1.0, u));
        float alive = step(0.0001, u);
        st = max(st, max(head * 0.95, ringH)) * alive;
        // grain in ink
        float grain = 0.86 + 0.14 * vnoise(vec3(uv * 520.0, float(i)));
        col *= mix(vec3(1.0), ink, clamp(st * grain, 0.0, 1.0));
        // arrival: ripples + disc fill
        float ta = t - t1;
        discFill[i] = smoothstep(0.0, 0.5, ta);
        if (ta > 0.0){
            for (int k = 0; k < 3; k++){
                float tk = ta - float(k) * 0.28;
                if (tk <= 0.0) continue;
                float rr = uRd + tk * 0.42;
                float fade = exp(-tk * 1.9);
                float ring = aa(abs(r - rr), 0.0016 + 0.0010 * float(k)) * fade;
                col *= mix(vec3(1.0), ink, ring * 0.9);
            }
            // burst dashes
            float dash = step(0.5, fract(phi / TAU * 28.0 + float(i) * 0.37 + 0.5)) * 0.0 + 1.0;
            float burst = aa(abs(r - (uRd + 0.025 + ta * 0.30)), 0.0012) * exp(-ta * 4.0) * step(0.5, fract(phi / TAU * 36.0));
            col *= mix(vec3(1.0), ink, burst);
        }
    }

    // ---- centre disc: 4 sectors filled with each ink
    if (r < uRd + 0.004){
        float sector = floor(mod(phi + PI, TAU) / (TAU / 4.0));
        int si = int(clamp(sector, 0.0, 3.0));
        float fillA = (si == 0) ? discFill[0] : (si == 1) ? discFill[1] : (si == 2) ? discFill[2] : discFill[3];
        float inside = aa(r - uRd, 0.0);
        // grow from the centre outwards
        float rev = smoothstep(0.0, 1.0, fillA);
        float m = inside * step(r, uRd * (0.15 + 0.85 * rev));
        vec3 ink = uInk[si];
        col *= mix(vec3(1.0), ink, m * 0.96);
        // overlay all inks lightly so the disc reads as one overprinted mark
        float allf = min(min(discFill[0], discFill[1]), min(discFill[2], discFill[3]));
        col *= mix(vec3(1.0), uInk[0] * 0.55 + 0.45, inside * allf * 0.5);
        col *= mix(vec3(1.0), uInk[3] * 0.6 + 0.4, inside * allf * 0.5);
    }
    // disc outline
    col *= mix(vec3(1.0), inkDark, aa(abs(r - uRd), 0.0010) * 0.9 * uFadeIn);

    // ---- gold ignition of the disc
    float gold = uGold;
    if (gold > 0.0){
        float g = aa(r - uRd * (1.0 + gold * 0.6), 0.0) * gold;
        vec3 gc = vec3(1.0, 0.40, 0.07);
        col = mix(col, gc * 1.9, g);
        col += gc * exp(-max(r - uRd, 0.0) * 14.0) * gold * 0.45;
    }
    col = max(col, 0.0) * 1.0;
    col += vec3(1.0, 0.97, 0.92) * uWhite;
    o = vec4(col, 1.0);
}
