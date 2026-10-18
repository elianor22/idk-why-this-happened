#version 430
uniform sampler2D uHdr;
uniform sampler2D uBloom;
uniform sampler2D uStreak;
uniform vec2 uRes;
uniform int uFrame;
uniform float uExposure;
uniform float uContrast;
uniform float uSat;
uniform vec3 uLift;
uniform vec3 uGain;
uniform vec3 uShadowTint;
uniform vec3 uHighTint;
uniform float uBloomAmt;
uniform float uStreakAmt;
uniform vec3 uStreakTint;
uniform float uVig;
uniform float uCA;
uniform float uGrain;
uniform float uTone;
uniform float uFade;     // master fade (1 = visible)
out vec4 o;
float luma(vec3 c);

const mat3 ACESIn = mat3(0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777);
const mat3 ACESOut = mat3(1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602);
vec3 RRT(vec3 v){ vec3 a = v*(v+0.0245786)-0.000090537; vec3 b = v*(0.983729*v+0.4329510)+0.238081; return a/b; }
vec3 aces(vec3 c){ c = ACESIn * (c * 0.6); c = RRT(c); c = ACESOut * c; return clamp(c, 0.0, 1.0); }
vec3 shoulder(vec3 x){ vec3 t = max(x - 0.78, 0.0); return min(x, vec3(0.78)) + 0.22 * (1.0 - exp(-t * 4.5)); }
uint pcgh(uint v){ uint s = v * 747796405u + 2891336453u; uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u; return (w >> 22u) ^ w; }
float rnd(uvec3 p){ return float(pcgh(p.x + pcgh(p.y + pcgh(p.z)))) * (1.0/4294967295.0); }
float tri(vec2 p, uint salt){ uvec2 q = uvec2(ivec2(p)); return rnd(uvec3(q, uint(uFrame) * 7u + salt)) + rnd(uvec3(q, uint(uFrame) * 13u + salt + 91u)) - 1.0; }

void main(){
    vec2 uv = gl_FragCoord.xy / uRes;
    vec2 d = uv - 0.5; d.x *= uRes.x / uRes.y;
    float r2 = dot(d, d);
    vec2 caOff = d * uCA * (0.4 + r2 * 3.0);
    vec3 c;
    c.r = texture(uHdr, uv + caOff / vec2(uRes.x/uRes.y, 1.0)).r;
    c.g = texture(uHdr, uv).g;
    c.b = texture(uHdr, uv - caOff / vec2(uRes.x/uRes.y, 1.0)).b;
    vec3 bl = texture(uBloom, uv).rgb;
    vec3 st = texture(uStreak, uv).rgb;
    c += bl * uBloomAmt + st * uStreakTint * uStreakAmt;
    c *= uExposure;
    // lift / gain / tints
    float l = luma(c);
    c = c * uGain + uLift;
    c = mix(c, c * uShadowTint, 1.0 - smoothstep(0.0, 0.5, l));
    c = mix(c, c * uHighTint, smoothstep(0.3, 1.5, l));
    float l2 = luma(c);
    c = mix(vec3(l2), c, uSat);
    // vignette
    float vig = 1.0 - uVig * smoothstep(0.15, 1.05, length(d) * 1.25);
    c *= vig;
    vec3 t = (uTone < 0.5) ? aces(c) : shoulder(max(c, 0.0));
    t = pow(t, vec3(1.0 / 2.2));
    t = (t - 0.5) * uContrast + 0.5;
    // grain (luma-weighted), dither
    float g = tri(gl_FragCoord.xy, 1u) * uGrain * (0.55 + 0.9 * (1.0 - abs(t.g - 0.45)));
    t += g + tri(gl_FragCoord.xy, 5u) / 255.0;
    t *= uFade;
    o = vec4(clamp(t, 0.0, 1.0), 1.0);
}
float luma(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
