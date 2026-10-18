#version 430
uniform vec2 uOrbL;
uniform vec2 uOrbR;
uniform vec2 uOrbI;
uniform float uHeadA;
uniform float uHeadB;
uniform vec2 uRing;
uniform float uGlow;
uniform float uClimax;
uniform float uFadeIn;
uniform float uYh;
uniform float uZoom;
uniform float uStarA;
out vec4 o;

const vec3 GOLD = vec3(1.0, 0.70, 0.34);
const vec3 ROSE = vec3(1.0, 0.42, 0.62);

vec3 skyGrad(vec2 uv){
    float h = uv.y - uYh;
    float g = uGlow;
    vec3 top = vec3(0.010, 0.008, 0.055);
    vec3 mid = mix(vec3(0.060, 0.030, 0.150), vec3(0.34, 0.09, 0.30), g);
    vec3 low = mix(vec3(0.30, 0.12, 0.22), vec3(1.0, 0.40, 0.26), g);
    vec3 hor = mix(vec3(0.70, 0.38, 0.30), vec3(1.0, 0.72, 0.42), g);
    vec3 c = mix(hor, low, smoothstep(0.0, 0.11, h));
    c = mix(c, mid, smoothstep(0.05, 0.26, h));
    c = mix(c, top, smoothstep(0.20, 0.62, h));
    float br = mix(0.28, 1.0, g);
    c *= mix(0.30, 1.0, smoothstep(0.45, 0.0, h)) * br * 0.80;
    // thin warm cirrus
    float cir = fbm(vec3(uv.x * 1.3 + uTime * 0.012, h * 7.5, uTime * 0.02), 5) * 0.5 + 0.5;
    float band = smoothstep(0.30, 0.80, cir) * smoothstep(0.0, 0.05, h) * smoothstep(0.55, 0.10, h);
    c += mix(vec3(0.55, 0.22, 0.30), vec3(1.0, 0.55, 0.38), g) * band * 0.22 * (0.4 + 0.8 * g);
    return c;
}

float starsF(vec2 uv){
    vec2 p = uv * 70.0; ivec2 id = ivec2(floor(p));
    float s = 0.0;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++){
        ivec2 c = id + ivec2(i, j);
        if (h12(c + 12) > 0.09) continue;
        vec2 sp = vec2(c) + h22(c + 3);
        float d = length(p - sp) / 70.0;
        s += (0.2 + 0.8 * h12(c + 4)) * exp(-d * d / (0.0011 * 0.0011)) * (0.6 + 0.4 * sin(uTime * 2.0 + h12(c) * 30.0));
    }
    return s;
}

vec3 orb(vec2 uv, vec2 c, float I, vec3 tint, float ringT){
    vec2 d = uv - c;
    float r = length(d);
    float core = exp(-r * r / (0.0105 * 0.0105)) * 5.0;
    float inner = exp(-r / 0.022) * 1.2;
    float halo = exp(-r / 0.075) * 0.55 + exp(-r / 0.30) * 0.20;
    float ang = atan(d.y, d.x);
    float spikes = pow(abs(cos(ang * 2.0 + 0.0)), 14.0) * exp(-r / 0.16) * 0.22 + pow(abs(cos(ang * 2.0 + 1.5708 + 0.4)), 24.0) * exp(-r / 0.10) * 0.12;
    vec3 col = mix(tint, vec3(1.0, 0.95, 0.85), 0.55) * core + tint * (inner + halo + spikes * 0.7);
    // bloom ring after answering
    if (ringT > 0.0){
        for (int k = 0; k < 3; k++){
            float tk = ringT - float(k) * 0.35;
            if (tk <= 0.0) continue;
            float R = 0.03 + tk * 0.34;
            col += tint * exp(-abs(r - R) / (0.004 + 0.002 * float(k))) * exp(-tk * 1.4) * 1.1;
        }
        col += tint * exp(-r / 0.12) * exp(-ringT * 2.2) * 2.0;
    }
    return col * I;
}

vec3 threads(vec2 uv){
    vec2 L = uOrbL, R = uOrbR;
    float dx = R.x - L.x;
    float s = (uv.x - L.x) / dx;
    if (s < -0.05 || s > 1.05) return vec3(0.0);
    float t = uTime;
    vec3 acc = vec3(0.0);
    const int N = 10;
    float freq = 2.6;
    for (int k = 0; k < N; k++){
        bool setA = (k % 2 == 0);
        float ph = TAU * float(k) / float(N);
        float sp = -t * 1.25;
        float A0 = 0.052 + 0.014 * float(k % 3);
        // amplitude envelope: narrow at the orbs, wide in the middle; grows as the braid forms
        float env = pow(max(sin(PI * clamp(s, 0.0, 1.0)), 0.0), 0.85);
        float arg = TAU * freq * s + ph + sp;
        float off = A0 * env * sin(arg);
        float arch = 0.085 * sin(PI * clamp(s, 0.0, 1.0));
        float yc = mix(L.y, R.y, s) + arch + off;
        // slope for distance correction
        float darg = TAU * freq / dx;
        float slope = A0 * env * cos(arg) * darg + 0.085 * PI * cos(PI * clamp(s, 0.0, 1.0)) / dx;
        float d = abs(uv.y - yc) / sqrt(1.0 + slope * slope);
        float depth = cos(arg);                       // front/back of the braid
        float w = 0.0022 * (0.5 + 0.5 * (0.5 + 0.5 * depth)) * (1.0 + 0.6 * env);
        float I = 0.55 + 0.45 * (0.5 + 0.5 * depth);
        // visibility along the path
        float vis;
        vec3 tint;
        if (setA){
            float head = uHeadA;
            vis = step(s, head) * (0.42 + 0.58 * smoothstep(head - 0.55, head, s));
            tint = GOLD;
        } else {
            float head = uHeadB;
            float sb = 1.0 - s;
            vis = step(sb, head) * (0.42 + 0.58 * smoothstep(head - 0.55, head, sb));
            tint = ROSE;
        }
        // once both have crossed, the braid stays lit
        float steady = smoothstep(0.55, 1.0, uClimax) * 0.0;
        float core = exp(-d * d / (w * w));
        float glow = exp(-d / (w * 9.0)) * 0.22;
        vec3 tc = mix(tint, vec3(1.0, 0.95, 0.88), core * 0.30);
        acc += tc * (core * 2.6 + glow * 1.6) * I * vis;
        // bright head
        float head2 = setA ? uHeadA : uHeadB;
        float hs = setA ? head2 : 1.0 - head2;
        if (head2 > 0.001 && head2 < 0.999){
            vec2 hp = vec2(L.x + dx * hs, mix(L.y, R.y, hs) + 0.085 * sin(PI * hs) + A0 * pow(max(sin(PI * hs), 0.0), 0.85) * sin(TAU * freq * hs + ph + sp));
            float dh = length(uv - hp);
            acc += tint * (exp(-dh * dh / (0.005 * 0.005)) * 1.6 + exp(-dh / 0.03) * 0.35) * I;
        }
    }
    return acc;
}

vec3 motes(vec2 uv){
    vec3 acc = vec3(0.0);
    float t = uTime;
    for (int i = 0; i < 70; i++){
        float h1 = h11(i * 7 + 1), h2 = h11(i * 7 + 2), h3 = h11(i * 7 + 3), h4 = h11(i * 7 + 4), h5 = h11(i * 7 + 5), h6 = h11(i * 7 + 6);
        vec2 p = vec2(mix(-0.95, 0.95, h1) + 0.03 * sin(t * (0.2 + h3) + h4 * 6.28), uYh + 0.01 + fract(h2 + t * 0.012 * (0.4 + h4)) * 0.72);
        float tw = 0.35 + 0.65 * (0.5 + 0.5 * sin(t * (0.8 + 2.5 * h5) + h6 * 6.28));
        float r = 0.0012 + 0.0022 * h3;
        float d = length(uv - p);
        float fadeY = smoothstep(0.0, 0.08, p.y - uYh) * smoothstep(0.78, 0.40, p.y - uYh);
        acc += mix(GOLD, vec3(1.0, 0.9, 0.8), 0.5) * exp(-d * d / (r * r)) * tw * fadeY * (0.6 + 1.2 * h6);
        acc += GOLD * exp(-d / (r * 9.0)) * 0.04 * tw * fadeY;
    }
    return acc;
}

vec3 rays(vec2 uv, vec2 c, vec3 tint, float amt){
    vec2 d = uv - c;
    float r = length(d);
    float a = atan(d.y, d.x);
    float n = fbm(vec3(cos(a) * 2.5, sin(a) * 2.5, uTime * 0.12), 4) * 0.5 + 0.5;
    float n2 = fbm(vec3(cos(a) * 6.0, sin(a) * 6.0, uTime * 0.2 + 5.0), 3) * 0.5 + 0.5;
    return tint * pow(n, 2.0) * (0.4 + n2) * exp(-r * 3.2) * amt * 0.32;
}

vec3 scene(vec2 uv){
    vec3 c = skyGrad(uv);
    c += vec3(0.9, 0.9, 1.0) * starsF(uv) * uStarA * smoothstep(0.08, 0.35, uv.y - uYh) * 0.7;
    // horizon haze
    float h = uv.y - uYh;
    c += mix(vec3(0.8, 0.40, 0.30), vec3(1.0, 0.75, 0.50), uGlow) * exp(-abs(h) * 22.0) * (0.12 + 0.35 * uGlow);
    // light rays after the climax
    c += rays(uv, uOrbL, GOLD, uClimax * uOrbI.x);
    c += rays(uv, uOrbR, ROSE, uClimax * uOrbI.y);
    c += orb(uv, uOrbL, uOrbI.x, GOLD, uRing.x);
    c += orb(uv, uOrbR, uOrbI.y, ROSE, uRing.y);
    c += threads(uv);
    c += motes(uv) * smoothstep(0.0, 1.0, uOrbI.x);
    return c;
}

vec3 water(vec2 uv){
    float dy = uYh - uv.y;
    float zw = 1.0 / max(dy, 0.001);
    vec2 w = vec2(uv.x * zw, zw);
    float t = uTime;
    vec2 sp = vec2(w.x * 0.22, w.y * 1.4);
    float h0 = fbm(vec3(sp, t * 0.12), 4);
    float hx = fbm(vec3(sp + vec2(0.04, 0.0), t * 0.12), 4);
    float hz = fbm(vec3(sp + vec2(0.0, 0.04), t * 0.12), 4);
    vec2 g = vec2(hx - h0, hz - h0) / 0.04;
    vec2 ruv = vec2(uv.x + g.x * 0.012 / (1.0 + 0.1 * zw), 2.0 * uYh - uv.y + g.y * 0.006);
    vec3 refl = scene(ruv);
    float fres = 0.30 + 0.55 * exp(-dy * 6.0);
    vec3 base = vec3(0.012, 0.010, 0.035) + mix(vec3(0.05, 0.02, 0.05), vec3(0.25, 0.10, 0.10), uGlow) * exp(-dy * 5.0);
    vec3 col = base + refl * fres * (0.75 - 0.35 * smoothstep(0.0, 0.5, dy));
    // glints
    float gl = smoothstep(0.35, 1.0, g.y) * exp(-dy * 3.0);
    col += vec3(1.0, 0.7, 0.5) * gl * 0.10 * (0.3 + uGlow);
    return col;
}

void main(){
    vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    uv /= uZoom;
    vec3 col = (uv.y >= uYh) ? scene(uv) : water(uv);
    col *= uFadeIn;
    o = vec4(col, 1.0);
}
