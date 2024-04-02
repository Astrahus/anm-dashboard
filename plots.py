from abc import ABC, abstractstaticmethod
import plotly.express as px


class Plot(ABC):
    @abstractstaticmethod
    def plot(self):
        pass


class Barplot(Plot):

    @staticmethod
    def plot(df, x, y, title, xlabel, height=600):
        fig = px.bar(
            data_frame=df,
            x=x,
            y=y,
            title=title,
            labels={"x": xlabel},
            text_auto=True,
            template="plotly_white",
        )
        fig.update_layout(height=height, yaxis={"autorange": "reversed", "title": ""})
        return fig


class Pieplot(Plot):

    @staticmethod
    def plot(df, names, values, title, height=600):
        fig = px.pie(
            data_frame=df,
            names=names,
            values=values,
            hole=0.5,
            title=title,
            template="plotly_white",
        )
        fig.update_layout(height=height)
        return fig


class Scatter(Plot):

    @staticmethod
    def plot(df, x, y, title, xlabel, ylabel):
        fig = px.scatter(
            data_frame=df,
            x=x,
            y=y,
            text=df.index,
            title=title,
            labels={"x": xlabel, "y": ylabel},
            template="plotly_white",
        )
        fig.update_layout(height=600)
        fig.update_traces(textposition="top center")
        return fig
