#version 430
uniform sampler2D uTex;
uniform vec2 uTexel;     // 1/source size
uniform int uFirst;
uniform float uThresh;
out vec4 o;
float luma(vec3 c){ return dot(c, vec3(0.2126,0.7152,0.0722)); }
void main(){
    vec2 uv = (floor(gl_FragCoord.xy) + 0.5) * (2.0 * uTexel);  // dest pixel -> src uv
    vec2 d = uTexel;
    vec3 a = textureLod(uTex, uv + d*vec2(-2,-2), 0).rgb;
    vec3 b = textureLod(uTex, uv + d*vec2( 0,-2), 0).rgb;
    vec3 c = textureLod(uTex, uv + d*vec2( 2,-2), 0).rgb;
    vec3 dd= textureLod(uTex, uv + d*vec2(-2, 0), 0).rgb;
    vec3 e = textureLod(uTex, uv, 0).rgb;
    vec3 f = textureLod(uTex, uv + d*vec2( 2, 0), 0).rgb;
    vec3 g = textureLod(uTex, uv + d*vec2(-2, 2), 0).rgb;
    vec3 h = textureLod(uTex, uv + d*vec2( 0, 2), 0).rgb;
    vec3 i = textureLod(uTex, uv + d*vec2( 2, 2), 0).rgb;
    vec3 j = textureLod(uTex, uv + d*vec2(-1,-1), 0).rgb;
    vec3 k = textureLod(uTex, uv + d*vec2( 1,-1), 0).rgb;
    vec3 l = textureLod(uTex, uv + d*vec2(-1, 1), 0).rgb;
    vec3 m = textureLod(uTex, uv + d*vec2( 1, 1), 0).rgb;
    vec3 r;
    if (uFirst == 1){
        vec3 g0 = (a+b+dd+e)*0.25, g1 = (b+c+e+f)*0.25, g2 = (dd+e+g+h)*0.25, g3 = (e+f+h+i)*0.25, g4 = (j+k+l+m)*0.25;
        g0 = max(g0 - uThresh, 0.0); g1 = max(g1 - uThresh, 0.0); g2 = max(g2 - uThresh, 0.0); g3 = max(g3 - uThresh, 0.0); g4 = max(g4 - uThresh, 0.0);
        float w0 = 1.0/(1.0+luma(g0)), w1 = 1.0/(1.0+luma(g1)), w2 = 1.0/(1.0+luma(g2)), w3 = 1.0/(1.0+luma(g3)), w4 = 1.0/(1.0+luma(g4));
        r = (g0*0.125*w0 + g1*0.125*w1 + g2*0.125*w2 + g3*0.125*w3 + g4*0.5*w4) / (0.125*(w0+w1+w2+w3) + 0.5*w4);
    } else {
        r = e*0.125 + (a+c+g+i)*0.03125 + (b+dd+f+h)*0.0625 + (j+k+l+m)*0.125;
    }
    o = vec4(r, 1.0);
}
