#version 430
uniform vec2 uSunC;
uniform float uRs;
uniform vec2 uEarthC;
uniform float uRe;
uniform float uLineY;
uniform float uLimbX;
uniform float uEdgeX;
uniform float uProg;
uniform float uTick[8];
uniform float uLit;
uniform float uFlash;
uniform float uArrT;       // seconds since arrival (<0 before)
uniform float uWhite;
uniform float uZoom;
uniform float uLineA;
uniform float uFadeOut;
out vec4 o;

vec3 sunSurface(vec2 sp, float rr, float t){
    float mu = sqrt(max(1.0 - rr * rr, 0.0));
    vec3 n = vec3(sp / uRs, mu);
    vec2 g = n.xy / (mu * 0.75 + 0.25);
    vec3 v1 = voronoi(g * 34.0 + vec2(0.0, t * 0.04), t * 0.9);
    vec3 v2 = voronoi(g * 12.0 + vec2(7.0, 0.0), t * 0.4);
    float fine = 1.0 - pow(clamp(v1.x * 1.2, 0.0, 1.0), 1.5);
    float coarse = 1.0 - pow(clamp(v2.x * 1.15, 0.0, 1.0), 1.4);
    float lane = smoothstep(0.6, 1.0, v1.x);
    float sg = fbm(vec3(n.xy * 3.2, t * 0.06), 4);
    float limb = 1.0 - 0.80 * pow(1.0 - mu, 1.15);
    float I = limb * (0.52 + 0.26 * fine + 0.20 * coarse + 0.32 * sg - 0.20 * lane);
    float spot = smoothstep(0.52, 0.68, fbm(vec3(n.xy * 2.4 + 4.0, 1.0 + t * 0.01), 3));
    I *= 1.0 - 0.8 * spot * smoothstep(0.0, 0.5, mu);
    I += 0.20 * smoothstep(0.40, 0.0, mu) * (0.4 + fine);
    return blackbody(clamp(I * 1.18 - 0.02, 0.0, 1.0)) * (0.12 + I * 1.8);
}

float prominence(vec2 sp, float ang, float rho, float t, float seed){
    vec2 q = rot(-ang) * sp;
    rho *= 1.0 + 0.10 * sin(t * 0.55 + seed * 6.0);
    q += 0.012 * vec2(fbm(vec3(q * 22.0, t * 0.3 + seed * 5.0), 3), fbm(vec3(q * 22.0 + 9.0, t * 0.3 + seed * 5.0), 3));
    vec2 c = vec2(uRs - rho * 0.30, 0.0);
    // loop squashed along the radial direction so it reads as an arch
    vec2 e = (q - c) * vec2(0.80, 1.0);
    float d = abs(length(e) - rho);
    float outside = smoothstep(uRs * 0.99, uRs * 1.012, length(q));
    float n = fbm(vec3(q * 55.0, t * 0.6 + seed * 13.0), 3) * 0.5 + 0.5;
    float arch = exp(-d / (0.0022 + 0.0016 * n)) * (0.5 + 1.8 * n);
    float haze = exp(-d / 0.014) * 0.10;
    return (arch + haze) * outside;
}

vec3 earth(vec2 ep, float t){
    float r = length(ep) / uRe;
    vec3 col = vec3(0.0);
    vec3 L = normalize(vec3(-0.96, 0.10, 0.28));
    if (r < 1.0){
        float z = sqrt(1.0 - r * r);
        vec3 n = vec3(ep / uRe, z);
        float dif = max(dot(n, L), 0.0);
        float wrap = clamp(dot(n, L) * 0.5 + 0.5, 0.0, 1.0);
        vec3 sp = n * 2.4 + vec3(t * 0.015, 0.0, 0.0);
        float land = smoothstep(0.02, 0.10, fbm(sp + vec3(3.0), 5));
        float cloud = smoothstep(0.05, 0.45, fbm(sp * 1.6 + vec3(0, 0, t * 0.03) + 9.0, 5));
        vec3 alb = mix(vec3(0.015, 0.06, 0.20), vec3(0.16, 0.26, 0.10), land);
        alb = mix(alb, vec3(0.9), cloud * 0.75);
        vec3 day = alb * dif * 3.0;
        // specular glint on ocean
        vec3 H = normalize(L + vec3(0, 0, 1));
        day += pow(max(dot(n, H), 0.0), 60.0) * (1.0 - land) * (1.0 - cloud) * 1.2;
        float rim = pow(1.0 - z, 3.0);
        vec3 atm = vec3(0.30, 0.58, 1.0) * rim * smoothstep(-0.25, 0.7, dot(n, L)) * 2.6;
        // night lights
        float city = smoothstep(0.62, 0.9, vnoise(sp * 22.0)) * land * (1.0 - cloud) * smoothstep(0.35, 0.0, dif);
        vec3 nightc = vec3(1.0, 0.62, 0.25) * city * 0.9;
        float litAmt = uLit;
        col = (day + atm) * litAmt + nightc * (0.35 + 0.65 * (1.0 - litAmt)) * 0.7;
        col += vec3(0.06, 0.12, 0.25) * rim * 0.5 * (1.0 - litAmt);
        col *= smoothstep(1.0, 0.985, r);
    } else {
        float x = r - 1.0;
        float side = smoothstep(-0.5, 0.8, dot(normalize(ep + 1e-5), normalize(L.xy)));
        col = vec3(0.25, 0.50, 1.0) * exp(-x * 22.0) * 0.55 * side * uLit;
    }
    return col;
}

void main(){
    vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    uv /= uZoom;
    float t = uTime;
    vec3 col = vec3(0.0);

    // --- space backdrop
    float vg = exp(-length(uv - vec2(-0.5, 0.0)) * 1.1);
    col += vec3(0.05, 0.020, 0.010) * vg * 0.35 + vec3(0.002, 0.003, 0.006);
    {
        vec2 p = uv * 60.0; ivec2 id = ivec2(floor(p));
        for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++){
            ivec2 c = id + ivec2(i, j);
            if (h12(c + 91) > 0.12) continue;
            vec2 sp = vec2(c) + h22(c + 5);
            float d = length(p - sp) / 60.0;
            float b = 0.04 + pow(h12(c + 3), 6.0);
            col += vec3(0.8, 0.85, 1.0) * b * exp(-d * d / (0.0011 * 0.0011)) * 0.9;
        }
    }

    vec2 sp = uv - uSunC;
    float r = length(sp);
    float rr = r / uRs;
    float ang = atan(sp.y, sp.x);

    // --- corona
    if (rr >= 0.9){
        float x = max(rr - 1.0, 0.0);
        float s = fbm(vec3(cos(ang) * 2.2, sin(ang) * 2.2, t * 0.05 + x * 1.2), 4) * 0.5 + 0.5;
        float s2 = fbm(vec3(cos(ang) * 6.0, sin(ang) * 6.0, t * 0.08 + x * 3.0 + 7.0), 3) * 0.5 + 0.5;
        float md = mix(0.25, 2.3, pow(s, 2.0)) * (0.45 + 1.1 * pow(s2, 2.0));
        float cor = 1.4 * exp(-x * 12.0) + 0.34 * exp(-x * 3.4) + 0.09 * exp(-x * 1.3);
        vec3 cc = mix(vec3(1.0, 0.86, 0.56), vec3(1.0, 0.30, 0.07), smoothstep(0.0, 1.1, x));
        col += cc * cor * md * smoothstep(0.9, 1.0, rr) * 0.8;
    }
    // --- prominences
    float pr = 0.0;
    pr += prominence(sp, 0.42, 0.105, t, 0.11);
    pr += prominence(sp, -0.58, 0.07, t, 0.47);
    col += vec3(1.0, 0.38, 0.11) * pr * 1.5;

    // --- sun disc
    if (rr < 1.0){
        vec3 sc = sunSurface(sp, rr, t);
        float edge = smoothstep(1.0, 0.994, rr);
        col = mix(col, sc, edge);
    }

    // --- Earth
    col += earth(uv - uEarthC, t);

    // --- light line, ticks
    float la = uLineA;
    float L0 = uLimbX, L1 = uEdgeX;
    float lx = clamp((uv.x - L0) / (L1 - L0), 0.0, 1.0);
    float onLine = smoothstep(0.0011, 0.0, abs(uv.y - uLineY)) * step(L0, uv.x) * step(uv.x, L1);
    float lit = step(uv.x, L0 + (L1 - L0) * uProg);
    col += vec3(0.95, 0.80, 0.60) * onLine * la * (0.14 + 0.9 * lit * exp(-(L0 + (L1 - L0) * uProg - uv.x) * 3.0));
    // dashed texture
    for (int k = 0; k < 8; k++){
        float fx = float(k + 1) * 60.0 / 499.0;
        float tx = L0 + (L1 - L0) * fx;
        float seg = smoothstep(0.0011, 0.0, sdSeg(uv, vec2(tx, uLineY - 0.014), vec2(tx, uLineY + 0.014)));
        col += vec3(1.0, 0.85, 0.62) * seg * la * (0.35 + 3.2 * uTick[k]);
        col += vec3(1.0, 0.7, 0.4) * exp(-length(uv - vec2(tx, uLineY)) / 0.018) * uTick[k] * 1.2;
    }
    // end caps
    col += vec3(0.95, 0.8, 0.6) * smoothstep(0.0011, 0.0, sdSeg(uv, vec2(L0, uLineY - 0.02), vec2(L0, uLineY + 0.02))) * la * 0.5;
    col += vec3(0.95, 0.8, 0.6) * smoothstep(0.0011, 0.0, sdSeg(uv, vec2(L1, uLineY - 0.02), vec2(L1, uLineY + 0.02))) * la * 0.5;

    // --- the photon
    if (uProg > 0.0005 && uArrT < 0.0){
        vec2 pp = vec2(L0 + (L1 - L0) * uProg, uLineY);
        float d = length(uv - pp);
        col += vec3(1.0, 0.93, 0.75) * (0.0020 / (d + 0.0020) * 2.2 + exp(-d / 0.030) * 1.0 + exp(-d / 0.008) * 1.5);
        float ax = abs(uv.x - pp.x), ay = abs(uv.y - pp.y);
        col += vec3(1.0, 0.85, 0.6) * (exp(-ay / 0.0016) * exp(-ax / 0.07) + exp(-ax / 0.0016) * exp(-ay / 0.05)) * 0.9;
    }
    // --- scattered radial photons
    for (int i = 0; i < 44; i++){
        float h1 = h11(i * 3 + 1), h2 = h11(i * 3 + 2), h3 = h11(i * 3 + 3);
        float a = mix(-1.15, 1.15, h1);
        vec2 dir = vec2(cos(a), sin(a));
        float sp_ = 0.085 + 0.02 * h3;
        float s = fract(h2 + t * sp_) * 1.9;
        vec2 pos = uSunC + dir * (uRs * 1.002 + s);
        float fade = smoothstep(0.0, 0.08, s) * smoothstep(1.9, 1.2, s);
        float d = sdSeg(uv, pos, pos - dir * (0.045 + 0.03 * h3));
        col += vec3(1.0, 0.72, 0.42) * smoothstep(0.0016, 0.0, d) * fade * 0.55 * (0.5 + h3);
        col += vec3(1.0, 0.8, 0.5) * exp(-length(uv - pos) / 0.006) * fade * 0.4 * (0.4 + h3);
    }

    // --- arrival burst
    if (uArrT >= 0.0){
        vec2 ep = uv - uEarthC;
        float d = length(ep);
        float f = uFlash;
        col += vec3(1.0, 0.92, 0.78) * (exp(-d / 0.02) * 3.0 + exp(-d / 0.09) * 1.2) * f;
        float ax = abs(ep.x), ay = abs(ep.y);
        col += vec3(1.0, 0.88, 0.7) * (exp(-ay / 0.0018) * exp(-ax / 0.26) + exp(-ax / 0.0018) * exp(-ay / 0.15)) * f * 1.3;
        float R = uRe + uArrT * 0.32;
        col += vec3(1.0, 0.8, 0.55) * exp(-abs(d - R) / 0.003) * exp(-uArrT * 1.7) * 1.4 * step(0.0, uArrT);
        col += vec3(1.0, 0.8, 0.55) * exp(-abs(d - R * 1.9) / 0.005) * exp(-uArrT * 2.4) * 0.5;
    }

    col *= uFadeOut;
    col += vec3(1.0, 0.95, 0.88) * uWhite;
    o = vec4(col, 1.0);
}
