from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


st.set_page_config(
    page_title="CRISP-DM Regression Explorer",
    page_icon="📈",
    layout="wide",
)


@dataclass(frozen=True)
class DataSpec:
    n: int
    variance: float
    seed: int
    noise_mean_range: float


@st.cache_data(show_spinner=False)
def generate_data(
    n: int,
    variance: float,
    seed: int,
    noise_mean_range: float,
) -> tuple[pd.DataFrame, dict[str, float]]:
    rng = np.random.default_rng(seed)
    x = rng.uniform(-100, 100, n)
    a = rng.uniform(-10, 10)
    b = rng.uniform(-50, 50)
    noise_mean = rng.uniform(-noise_mean_range, noise_mean_range)
    noise = rng.normal(loc=noise_mean, scale=np.sqrt(variance), size=n)
    y = a * x + b + noise

    df = pd.DataFrame({"x": x, "y": y})
    truth = {
        "a": float(a),
        "b": float(b),
        "noise_mean": float(noise_mean),
        "noise_mean_range": float(noise_mean_range),
        "variance": float(variance),
    }
    return df, truth


@st.cache_resource(show_spinner=False)
def fit_model(data: pd.DataFrame, seed: int) -> dict[str, object]:
    x = data[["x"]].to_numpy()
    y = data["y"].to_numpy()

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=seed,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = LinearRegression()
    model.fit(x_train_scaled, y_train)

    y_pred = model.predict(x_test_scaled)
    mse = mean_squared_error(y_test, y_pred)
    rmse = float(np.sqrt(mse))
    r2 = r2_score(y_test, y_pred)

    coef_scaled = float(model.coef_[0])
    learned_slope = coef_scaled / float(scaler.scale_[0])
    learned_intercept = float(model.intercept_) - learned_slope * float(scaler.mean_[0])

    return {
        "model": model,
        "scaler": scaler,
        "x_train": x_train,
        "x_test": x_test,
        "y_train": y_train,
        "y_test": y_test,
        "y_pred": y_pred,
        "mse": float(mse),
        "rmse": rmse,
        "r2": float(r2),
        "learned_slope": float(learned_slope),
        "learned_intercept": float(learned_intercept),
    }


@st.cache_data(show_spinner=False)
def make_regression_line(
    x_min: float,
    x_max: float,
    learned_slope: float,
    learned_intercept: float,
) -> pd.DataFrame:
    x_line = np.linspace(x_min, x_max, 200)
    y_line = learned_slope * x_line + learned_intercept
    return pd.DataFrame({"x": x_line, "y": y_line})


def predict_x(x_value: float, scaler: StandardScaler, model: LinearRegression) -> float:
    x_scaled = scaler.transform(np.array([[x_value]], dtype=float))
    return float(model.predict(x_scaled)[0])


def serialize_model_package(
    scaler: StandardScaler,
    model: LinearRegression,
    metadata: dict[str, object],
) -> bytes:
    buffer = BytesIO()
    joblib.dump(
        {
            "scaler": scaler,
            "model": model,
            "metadata": metadata,
        },
        buffer,
    )
    buffer.seek(0)
    return buffer.getvalue()


def plot_scatter_with_line(data: pd.DataFrame, line: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.scatter(data["x"], data["y"], s=22, alpha=0.56, color="#2F6F8F", edgecolors="none")
    ax.plot(line["x"], line["y"], color="#D1495B", linewidth=2.6, label="Regression line")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.22)
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()
    return fig


def ensure_session_defaults() -> None:
    if "data_spec" not in st.session_state:
        st.session_state.data_spec = DataSpec(n=300, variance=100.0, seed=42, noise_mean_range=10.0)
        return

    current = st.session_state.data_spec
    st.session_state.data_spec = DataSpec(
        n=current.n,
        variance=current.variance,
        seed=current.seed,
        noise_mean_range=getattr(current, "noise_mean_range", 10.0),
    )


ensure_session_defaults()

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.55rem; }
    .crisp-note {
        border-left: 4px solid #2F6F8F;
        padding: 0.6rem 0 0.6rem 0.9rem;
        color: #334155;
        background: #F8FAFC;
        margin: 0.25rem 0 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Data Generator")
    n_input = st.slider("n", min_value=100, max_value=1000, value=st.session_state.data_spec.n, step=50)
    variance_input = st.slider(
        "Variance",
        min_value=0.0,
        max_value=10000.0,
        value=float(st.session_state.data_spec.variance),
        step=50.0,
        help="Higher variance makes points spread farther from the regression line.",
    )
    noise_mean_range_input = st.slider(
        "Noise mean range (+/-)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.data_spec.noise_mean_range),
        step=1.0,
        help="The noise mean is sampled from Uniform(-range, range).",
    )
    seed_input = st.slider("Seed", min_value=0, max_value=10_000, value=st.session_state.data_spec.seed, step=1)

    if st.button("Generate Data", type="primary", width="stretch"):
        st.session_state.data_spec = DataSpec(
            n=n_input,
            variance=variance_input,
            seed=seed_input,
            noise_mean_range=noise_mean_range_input,
        )

    st.divider()
    st.caption("Generation is deterministic for the selected seed.")

spec = st.session_state.data_spec
data, truth = generate_data(spec.n, spec.variance, spec.seed, spec.noise_mean_range)
fit = fit_model(data, spec.seed)
line = make_regression_line(
    float(data["x"].min()),
    float(data["x"].max()),
    float(fit["learned_slope"]),
    float(fit["learned_intercept"]),
)

st.title("CRISP-DM Regression Explorer")
st.caption("Linear regression with generated data, scaling, train/test evaluation, and joblib export.")

overview_left, overview_right = st.columns([1.3, 1])
with overview_left:
    st.pyplot(plot_scatter_with_line(data, line), clear_figure=True)
with overview_right:
    st.subheader("Current Run")
    run_cols = st.columns(4)
    run_cols[0].metric("Rows", f"{spec.n:,}")
    run_cols[1].metric("Variance", f"{spec.variance:,.0f}")
    run_cols[2].metric("Noise mean range", f"+/-{spec.noise_mean_range:,.0f}")
    run_cols[3].metric("Seed", spec.seed)

    metric_cols = st.columns(3)
    metric_cols[0].metric("MSE", f"{fit['mse']:,.3f}")
    metric_cols[1].metric("RMSE", f"{fit['rmse']:,.3f}")
    metric_cols[2].metric("R²", f"{fit['r2']:.4f}")

    x_value = st.number_input(
        "Predict y for x",
        min_value=-1_000.0,
        max_value=1_000.0,
        value=0.0,
        step=1.0,
    )
    prediction = predict_x(float(x_value), fit["scaler"], fit["model"])
    st.metric("Predicted y", f"{prediction:,.3f}")

tabs = st.tabs(
    [
        "Business Understanding",
        "Data Understanding",
        "Data Preparation",
        "Modeling",
        "Evaluation",
        "Deployment",
    ]
)

with tabs[0]:
    st.markdown(
        """
        <div class="crisp-note">
        Goal: estimate the linear relationship between x and y from noisy synthetic data,
        then use the learned model for prediction.
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Target", "y")
    c2.metric("Feature", "x")
    c3.metric("Method", "LinearRegression")
    st.write(
        "The generated process is `y = a*x + b + noise`. "
        "Because noise can have a non-zero mean, the learned intercept often tracks `b + noise_mean`."
    )

with tabs[1]:
    st.markdown('<div class="crisp-note">Inspect the generated sample and the hidden data process.</div>', unsafe_allow_html=True)
    d1, d2 = st.columns([1, 1])
    with d1:
        st.dataframe(data.head(20), width="stretch", hide_index=True)
    with d2:
        st.subheader("Generated Parameters")
        st.table(
            pd.DataFrame(
                {
                    "Parameter": ["a", "b", "noise mean", "noise mean range", "noise variance"],
                    "Value": [
                        f"{truth['a']:.6f}",
                        f"{truth['b']:.6f}",
                        f"{truth['noise_mean']:.6f}",
                        f"+/-{truth['noise_mean_range']:.6f}",
                        f"{truth['variance']:.6f}",
                    ],
                }
            )
        )
        st.subheader("Data Summary")
        st.dataframe(data.describe().T, width="stretch")

with tabs[2]:
    st.markdown(
        '<div class="crisp-note">Split the sample and standardize x before fitting the regression model.</div>',
        unsafe_allow_html=True,
    )
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Train rows", f"{len(fit['x_train']):,}")
    p2.metric("Test rows", f"{len(fit['x_test']):,}")
    p3.metric("Scaler mean", f"{float(fit['scaler'].mean_[0]):,.3f}")
    p4.metric("Scaler scale", f"{float(fit['scaler'].scale_[0]):,.3f}")
    st.code(
        "train_test_split(test_size=0.25) → StandardScaler.fit_transform(train) → StandardScaler.transform(test)",
        language="text",
    )

with tabs[3]:
    st.markdown('<div class="crisp-note">Fit scikit-learn LinearRegression on the scaled training data.</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("True a", f"{truth['a']:.4f}")
    m2.metric("Learned slope", f"{fit['learned_slope']:.4f}")
    m3.metric("True b", f"{truth['b']:.4f}")
    m4.metric("Learned intercept", f"{fit['learned_intercept']:.4f}")

    params = pd.DataFrame(
        {
            "Parameter": ["slope", "intercept"],
            "True value": [truth["a"], truth["b"]],
            "Learned value": [fit["learned_slope"], fit["learned_intercept"]],
            "Difference": [
                fit["learned_slope"] - truth["a"],
                fit["learned_intercept"] - truth["b"],
            ],
        }
    )
    st.dataframe(params, width="stretch", hide_index=True)

with tabs[4]:
    st.markdown('<div class="crisp-note">Evaluate predictions on the held-out test set.</div>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    e1.metric("MSE", f"{fit['mse']:,.3f}")
    e2.metric("RMSE", f"{fit['rmse']:,.3f}")
    e3.metric("R²", f"{fit['r2']:.4f}")

    residuals = pd.DataFrame(
        {
            "x": fit["x_test"].ravel(),
            "actual_y": fit["y_test"],
            "predicted_y": fit["y_pred"],
        }
    )
    residuals["residual"] = residuals["actual_y"] - residuals["predicted_y"]
    st.dataframe(residuals.head(25), width="stretch", hide_index=True)

with tabs[5]:
    st.markdown(
        '<div class="crisp-note">Package the scaler, model, and run metadata for reuse.</div>',
        unsafe_allow_html=True,
    )
    metadata = {
        "n": spec.n,
        "variance": spec.variance,
        "seed": spec.seed,
        "true_a": truth["a"],
        "true_b": truth["b"],
        "noise_mean": truth["noise_mean"],
        "noise_mean_range": truth["noise_mean_range"],
        "mse": fit["mse"],
        "rmse": fit["rmse"],
        "r2": fit["r2"],
        "learned_slope": fit["learned_slope"],
        "learned_intercept": fit["learned_intercept"],
    }
    model_bytes = serialize_model_package(fit["scaler"], fit["model"], metadata)
    st.download_button(
        "Download joblib model",
        data=model_bytes,
        file_name="crispdm_linear_regression.joblib",
        mime="application/octet-stream",
        width="stretch",
    )
    st.json(metadata)
